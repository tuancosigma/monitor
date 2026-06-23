"""Benchmark run model: k6 throughput/latency results stored over time."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    scenario: Mapped[str] = mapped_column(String(50))  # ingest_throughput, query_latency
    # primary metric (events/s for ingest, ms p95 for latency)
    metric_value: Mapped[float] = mapped_column(Float)
    metric_unit: Mapped[str] = mapped_column(String(20))
    passed: Mapped[bool] = mapped_column(default=False)  # met the P1 target?
    raw_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class BenchmarkRunResponse(BaseModel):
    id: int
    ts: datetime
    scenario: str
    metric_value: float
    metric_unit: str
    passed: bool
    model_config = {"from_attributes": True}
