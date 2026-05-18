import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings

ALGO = "HS256"


def issue_token(user_id: str) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.jwt_ttl_days)
    payload = {"sub": user_id, "iat": int(now.timestamp()), "exp": int(expires_at.timestamp())}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)
    return token, expires_at


def decode_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    return payload["sub"]


def make_oauth_state(guest_id: str | None) -> str:
    """Signed, short-lived state for the Google OAuth round-trip.

    Carries CSRF nonce + the guest user_id (if any) so the callback can
    upgrade-in-place without re-presenting the bearer token.
    """
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "guest_id": guest_id,
        "exp": int((datetime.now(UTC) + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def parse_oauth_state(state: str) -> str | None:
    payload = jwt.decode(state, settings.jwt_secret, algorithms=[ALGO])
    return payload.get("guest_id")
