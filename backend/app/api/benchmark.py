"""Benchmark API: list k6 results + trigger a scenario run (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.benchmark import k6_harness
from app.core.metadata_db import get_db
from app.core.rbac import require_role
from app.models.benchmark_run import BenchmarkRun, BenchmarkRunResponse

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


@router.get("", response_model=list[BenchmarkRunResponse])
async def list_benchmarks(db: AsyncSession = Depends(get_db)) -> list[BenchmarkRun]:
    return list(
        (await db.execute(select(BenchmarkRun).order_by(desc(BenchmarkRun.ts)).limit(100)))
        .scalars()
        .all()
    )


@router.post(
    "/run", response_model=BenchmarkRunResponse, dependencies=[Depends(require_role("admin"))]
)
async def run_benchmark(
    scenario: str = "ingest_throughput", db: AsyncSession = Depends(get_db)
) -> BenchmarkRun:
    try:
        return await k6_harness.run_k6(db, scenario)
    except RuntimeError as err:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
