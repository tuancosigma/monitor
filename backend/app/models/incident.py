"""Incident model definitions (SQLAlchemy + Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.metadata_db import Base

if TYPE_CHECKING:
    from app.models.alert import Alert, AlertResponse


class Incident(Base):
    """Incident SQLAlchemy model."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1000))
    severity: Mapped[str] = mapped_column(String(50))  # info, low, medium, high, critical
    # status options: open, investigating, resolved, closed
    status: Mapped[str] = mapped_column(String(50), default="open", index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    entities: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)

    alerts: Mapped[list[Alert]] = relationship(
        "Alert", back_populates="incident", cascade="all, delete-orphan"
    )


# ============================================================================
# Pydantic Schemas
# ============================================================================


class IncidentBase(BaseModel):
    title: str
    description: str
    severity: str
    status: str
    first_seen: datetime
    last_seen: datetime
    entities: list[dict[str, Any]] = Field(default_factory=list)
    assignee: str | None = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    status: str | None = None
    assignee: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None


class IncidentResponse(IncidentBase):
    id: int

    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    alerts: list[AlertResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


from app.models.alert import AlertResponse

IncidentDetailResponse.model_rebuild()
