"""Playbook + PlaybookRun models (SQLAlchemy + Pydantic).

A playbook is a DAG: ``nodes`` = [{id, action, params}], ``edges`` = [[from_id, to_id]].
Triggers bind it to alert/incident/cron/webhook events. ``auto_approve`` lets dangerous
actions run without an interactive confirmation gate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # trigger_type: alert, incident, cron, webhook
    trigger_type: Mapped[str] = mapped_column(String(50), index=True)
    trigger_filter: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    edges: Mapped[list[list[str]]] = mapped_column(JSON, default=list)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PlaybookRun(Base):
    __tablename__ = "playbook_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    playbook_id: Mapped[int] = mapped_column(
        ForeignKey("playbooks.id", ondelete="CASCADE"), index=True
    )
    # status: success, failed, dry_run, blocked
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # node_results: [{node_id, action, status, output, planned}]
    node_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    node_count: Mapped[int] = mapped_column(Integer, default=0)


# ============================================================================
# Pydantic Schemas
# ============================================================================


class PlaybookNode(BaseModel):
    id: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class PlaybookBase(BaseModel):
    name: str
    trigger_type: str
    trigger_filter: dict[str, Any] = Field(default_factory=dict)
    nodes: list[PlaybookNode] = Field(default_factory=list)
    edges: list[list[str]] = Field(default_factory=list)
    auto_approve: bool = False
    is_active: bool = True


class PlaybookCreate(PlaybookBase):
    pass


class PlaybookUpdate(BaseModel):
    name: str | None = None
    trigger_filter: dict[str, Any] | None = None
    nodes: list[PlaybookNode] | None = None
    edges: list[list[str]] | None = None
    auto_approve: bool | None = None
    is_active: bool | None = None


class PlaybookResponse(PlaybookBase):
    id: int
    model_config = {"from_attributes": True}


class PlaybookRunResponse(BaseModel):
    id: int
    playbook_id: int
    status: str
    dry_run: bool
    node_results: list[dict[str, Any]]
    node_count: int
    model_config = {"from_attributes": True}
