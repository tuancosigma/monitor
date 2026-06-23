"""NotificationLog model definitions (SQLAlchemy + Pydantic)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.metadata_db import Base

if TYPE_CHECKING:
    from app.models.channel import Channel


class NotificationLog(Base):
    """NotificationLog SQLAlchemy model."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    # Status values: sent, failed, skipped_silenced, skipped_dedup, rate_limited
    status: Mapped[str] = mapped_column(String(50), index=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_escalation: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    channel: Mapped[Channel] = relationship("Channel")


# ============================================================================
# Pydantic Schemas
# ============================================================================


class NotificationLogBase(BaseModel):
    alert_id: int | None = None
    incident_id: int | None = None
    channel_id: int
    status: str
    sent_at: datetime
    error_message: str | None = None
    is_escalation: bool = False
    retry_count: int = 0


class NotificationLogCreate(NotificationLogBase):
    pass


class NotificationLogResponse(NotificationLogBase):
    id: int

    model_config = {"from_attributes": True}
