"""Dashboard layout model: per-owner widget grid persisted as JSON."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # widgets: [{id, type, title, query, x, y, w, h}]
    widgets: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class DashboardLayoutPayload(BaseModel):
    owner: str = "default"
    widgets: list[dict[str, Any]] = Field(default_factory=list)


class DashboardLayoutResponse(BaseModel):
    owner: str
    widgets: list[dict[str, Any]]
    model_config = {"from_attributes": True}
