"""Alert model definitions (SQLAlchemy + Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.metadata_db import Base

if TYPE_CHECKING:
    from app.models.incident import Incident


class Alert(Base):
    """Alert SQLAlchemy model."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rule_id: Mapped[str] = mapped_column(String(255), index=True)
    rule_name: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(50))  # info, low, medium, high, critical
    # status options: open, acknowledged, resolved, false_positive
    status: Mapped[str] = mapped_column(String(50), default="open", index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    dedup_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    entities: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    mitre_mapping: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    sample_events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)

    incident: Mapped[Incident | None] = relationship("Incident", back_populates="alerts")


# ============================================================================
# Pydantic Schemas
# ============================================================================


class AlertBase(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    status: str
    timestamp: datetime
    dedup_key: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    mitre_mapping: list[dict[str, Any]] = Field(default_factory=list)
    sample_events: list[dict[str, Any]] = Field(default_factory=list)
    incident_id: int | None = None
    assignee: str | None = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: str | None = None
    assignee: str | None = None
    incident_id: int | None = None


class AlertResponse(AlertBase):
    id: int

    model_config = {"from_attributes": True}
