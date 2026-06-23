"""Posture run model: a security-benchmark snapshot (CIS-style score + findings)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class PostureRun(Base):
    __tablename__ = "posture_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    tool: Mapped[str] = mapped_column(String(50))  # trivy, lynis
    score: Mapped[float] = mapped_column(Float)  # 0..100 CIS-style
    drift: Mapped[float] = mapped_column(Float, default=0.0)  # delta vs previous run
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)


class PostureRunResponse(BaseModel):
    id: int
    ts: datetime
    tool: str
    score: float
    drift: float
    findings: list[dict[str, Any]]
    total_findings: int
    model_config = {"from_attributes": True}
