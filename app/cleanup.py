from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User


async def purge_expired_guests(session: AsyncSession) -> int:
    """Delete guest users that have been inactive past GUEST_TTL_DAYS.

    Run periodically from a cron / scheduled job. Returns count deleted.
    """
    cutoff = datetime.now(UTC) - timedelta(days=settings.guest_ttl_days)
    result = await session.execute(
        delete(User).where(User.is_guest.is_(True), User.last_seen_at < cutoff)
    )
    await session.commit()
    return result.rowcount or 0
