from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.jwt_utils import decode_token
from app.models import User

# Single shared scheme so Swagger UI shows one "Authorize" button at the top.
# auto_error=False because HTTPBearer's default is 403, but missing-auth is 401;
# we raise 401 ourselves in current_user, and signup/login/google_login treat the
# bearer as optional for the guest-upgrade flow.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT from /auth/guest, /auth/signup, /auth/login, or /auth/google/callback",
)

OptionalBearer = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def current_user(
    creds: OptionalBearer,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        user_id = decode_token(creds.credentials)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}") from e

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    user.last_seen_at = datetime.now(UTC)
    await session.commit()
    return user
