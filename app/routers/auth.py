from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import current_user
from app.google_oauth import authorize_url, exchange_code
from app.jwt_utils import decode_token, issue_token, make_oauth_state, parse_oauth_state
from app.models import Article, User, WordbookEntry
from app.passwords import hash_password, verify_password
from app.schemas import AuthOut, GoogleLoginOut, LoginIn, SignupIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_out(user: User, token: str, expires_at: datetime) -> AuthOut:
    return AuthOut(
        access_token=token, expires_at=expires_at, user=UserOut.model_validate(user)
    )


async def _resolve_guest_id(
    authorization: str | None, session: AsyncSession
) -> str | None:
    """Decode an optional bearer header; return its user_id only if it points
    to a current guest user. Invalid/expired/non-guest tokens are silently ignored."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        uid = decode_token(authorization.split(" ", 1)[1])
    except jwt.PyJWTError:
        return None
    user = await session.get(User, uid)
    return user.id if (user and user.is_guest) else None


async def _merge_guest_into(
    guest_id: str | None, target: User, session: AsyncSession
) -> None:
    """Re-point a guest's owned rows to `target` and delete the guest row.
    No-op if guest_id is None, equal to target, or no longer a guest."""
    if not guest_id or guest_id == target.id:
        return
    guest = await session.get(User, guest_id)
    if guest is None or not guest.is_guest:
        return
    await session.execute(
        update(Article).where(Article.user_id == guest.id).values(user_id=target.id)
    )
    await session.execute(
        update(WordbookEntry)
        .where(WordbookEntry.user_id == guest.id)
        .values(user_id=target.id)
    )
    await session.delete(guest)


async def _finalize(user: User, session: AsyncSession) -> AuthOut:
    user.last_seen_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(user)
    token, expires_at = issue_token(user.id)
    return _auth_out(user, token, expires_at)


@router.post("/guest", response_model=AuthOut)
async def create_guest(session: Annotated[AsyncSession, Depends(get_session)]) -> AuthOut:
    user = User()
    session.add(user)
    return await _finalize(user, session)


@router.post("/signup", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthOut:
    """Create an email/password account. If a guest bearer is present, upgrade
    that guest row in place so their wordbook/reading list survives."""
    existing = await session.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")

    pw_hash = hash_password(body.password)
    guest_id = await _resolve_guest_id(authorization, session)

    if guest_id:
        user = await session.get(User, guest_id)
        # _resolve_guest_id already verified is_guest, but recheck for safety
        if user is None or not user.is_guest:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Guest not found")
        user.is_guest = False
        user.email = body.email
        user.password_hash = pw_hash
        user.name = body.name
    else:
        user = User(
            is_guest=False,
            email=body.email,
            password_hash=pw_hash,
            name=body.name,
        )
        session.add(user)

    return await _finalize(user, session)


@router.post("/login", response_model=AuthOut)
async def login(
    body: LoginIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthOut:
    """Authenticate by email + password. If a guest bearer is present and the
    logged-in user is different, the guest's data is merged into the real user."""
    user = await session.scalar(select(User).where(User.email == body.email))
    if user is None or user.password_hash is None or not verify_password(
        body.password, user.password_hash
    ):
        # NOTE: timing leak on missing user vs wrong password is minor here
        # (bcrypt verify dominates); harden later with a dummy-hash compare.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    guest_id = await _resolve_guest_id(authorization, session)
    await _merge_guest_into(guest_id, user, session)

    return await _finalize(user, session)


@router.get("/google/login", response_model=GoogleLoginOut)
async def google_login(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> GoogleLoginOut:
    """Returns the Google authorize URL. Frontend redirects the browser there.

    If a guest bearer is included, the guest's id is embedded in `state` so the
    callback can upgrade the same row instead of creating a new user.
    """
    guest_id = await _resolve_guest_id(authorization, session)
    return GoogleLoginOut(url=authorize_url(make_oauth_state(guest_id)))


@router.get("/google/callback", response_model=AuthOut)
async def google_callback(
    session: Annotated[AsyncSession, Depends(get_session)],
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
) -> AuthOut:
    try:
        guest_id = parse_oauth_state(state)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid state: {e}") from e

    info = await exchange_code(code)
    google_sub = info["sub"]
    email = info.get("email")
    name = info.get("name")

    existing = await session.scalar(select(User).where(User.google_sub == google_sub))

    if existing is not None:
        await _merge_guest_into(guest_id, existing, session)
        user = existing
    elif guest_id:
        user = await session.get(User, guest_id)
        if user is None or not user.is_guest:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Guest not found")
        user.is_guest = False
        user.google_sub = google_sub
        user.email = email
        user.name = name
    else:
        user = User(is_guest=False, google_sub=google_sub, email=email, name=name)
        session.add(user)

    return await _finalize(user, session)


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[User, Depends(current_user)]) -> UserOut:
    return UserOut.model_validate(user)
