"""Audit log model (append-only): actor + action + target for every mutation."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    actor: Mapped[str] = mapped_column(String(255), default="anonymous", index=True)
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(512))
    status_code: Mapped[int] = mapped_column(Integer)


class AuditLogResponse(BaseModel):
    id: int
    ts: datetime
    actor: str
    method: str
    path: str
    status_code: int
    model_config = {"from_attributes": True}
