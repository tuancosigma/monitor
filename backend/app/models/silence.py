"""Silence model definitions (SQLAlchemy + Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class Silence(Base):
    """Silence SQLAlchemy model."""

    __tablename__ = "silences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # filters shape: {"severity": ["low"], "rule_id": "...", "entity_value": "..."}
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ============================================================================
# Pydantic Schemas
# ============================================================================


class SilenceBase(BaseModel):
    name: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    start_time: datetime
    end_time: datetime
    is_active: bool = True


class SilenceCreate(SilenceBase):
    pass


class SilenceUpdate(BaseModel):
    name: str | None = None
    filters: dict[str, Any] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None


class SilenceResponse(SilenceBase):
    id: int

    model_config = {"from_attributes": True}
