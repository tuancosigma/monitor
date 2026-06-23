"""Channel model definitions (SQLAlchemy + Pydantic)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class Channel(Base):
    """Channel SQLAlchemy model."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    # type options: slack, telegram, discord, smtp, webhook
    type: Mapped[str] = mapped_column(String(50), index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ChannelBase(BaseModel):
    name: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class ChannelResponse(ChannelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
