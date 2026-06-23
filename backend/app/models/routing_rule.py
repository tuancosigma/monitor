"""RoutingRule model definitions (SQLAlchemy + Pydantic)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.metadata_db import Base
from app.models.channel import ChannelResponse

if TYPE_CHECKING:
    from app.models.channel import Channel


class RoutingRule(Base):
    """RoutingRule SQLAlchemy model."""

    __tablename__ = "routing_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    # criteria shape: {"severities": ["high", "critical"], "rule_ids": [], "tags": []}
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    escalation_delay_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    channel: Mapped[Channel] = relationship("Channel")


# ============================================================================
# Pydantic Schemas
# ============================================================================


class RoutingRuleBase(BaseModel):
    name: str
    criteria: dict[str, Any] = Field(default_factory=dict)
    channel_id: int
    is_active: bool = True
    escalation_delay_min: int | None = None


class RoutingRuleCreate(RoutingRuleBase):
    pass


class RoutingRuleUpdate(BaseModel):
    name: str | None = None
    criteria: dict[str, Any] | None = None
    channel_id: int | None = None
    is_active: bool | None = None
    escalation_delay_min: int | None = None


class RoutingRuleResponse(RoutingRuleBase):
    id: int
    channel: ChannelResponse | None = None

    model_config = {"from_attributes": True}
