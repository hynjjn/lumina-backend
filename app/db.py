from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_pg_url(raw: str) -> str:
    # Accept Neon/Heroku-style URLs verbatim and rewrite them for asyncpg:
    # force the +asyncpg driver, drop libpq-only params (sslmode, channel_binding),
    # and translate sslmode → asyncpg's ssl arg.
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    url = make_url(raw)
    if "+" not in url.drivername:
        url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode
    return url.set(query=query).render_as_string(hide_password=False)


def _build_engine():
    url = settings.database_url
    if url.startswith(("postgresql", "postgres")):
        # asyncpg + PgBouncer/Neon pooler in transaction mode doesn't support
        # server-side prepared statements; disable the cache to avoid errors.
        return create_async_engine(
            _normalize_pg_url(url),
            echo=False,
            pool_pre_ping=True,
            connect_args={"statement_cache_size": 0},
        )
    return create_async_engine(url, echo=False)


engine = _build_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


if settings.database_url.startswith("sqlite"):
    # SQLite does not enforce FK constraints unless this PRAGMA is set per connection.
    # Required for ON DELETE CASCADE on guest user GC.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
