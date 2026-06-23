"""Posture API: list runs + trigger a Trivy/Lynis scan (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.benchmark import posture as posture_mod
from app.core.metadata_db import get_db
from app.core.rbac import require_role
from app.models.posture_run import PostureRun, PostureRunResponse

router = APIRouter(prefix="/api/posture", tags=["posture"])


@router.get("", response_model=list[PostureRunResponse])
async def list_posture(db: AsyncSession = Depends(get_db)) -> list[PostureRun]:
    return list(
        (await db.execute(select(PostureRun).order_by(desc(PostureRun.ts)).limit(50)))
        .scalars()
        .all()
    )


@router.post(
    "/run", response_model=PostureRunResponse, dependencies=[Depends(require_role("admin"))]
)
async def run_posture(tool: str = "trivy", db: AsyncSession = Depends(get_db)) -> PostureRun:
    try:
        return await posture_mod.run_posture(db, tool)
    except RuntimeError as err:  # tool not installed on this host
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
