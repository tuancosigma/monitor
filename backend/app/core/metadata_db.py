"""SQLAlchemy metadata database setup.

Configures connection pooling and transaction lifecycle helpers for stateful tables
like Alerts and Incidents.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.metadata_db_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.metadata_db_url.startswith("sqlite")
        else {}
    ),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy metadata models."""
    pass


async def init_db() -> None:
    """Create all SQLAlchemy metadata tables (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an async session for database operations."""
    async with AsyncSessionLocal() as session:
        yield session
