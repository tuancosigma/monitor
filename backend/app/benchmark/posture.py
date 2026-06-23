"""Posture orchestration: run a tool, compute drift vs the previous run, persist."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.benchmark import lynis, trivy
from app.models.posture_run import PostureRun


async def _previous_score(db: AsyncSession, tool: str) -> float | None:
    row = (
        await db.execute(
            select(PostureRun).where(PostureRun.tool == tool).order_by(desc(PostureRun.ts)).limit(1)
        )
    ).scalar_one_or_none()
    return row.score if row else None


async def run_posture(
    db: AsyncSession, tool: str, *, target: str = "sentinel-backend"
) -> PostureRun:
    """Run a posture tool, compute CIS-style score + drift, and persist the run.

    ``tool`` is 'trivy' or 'lynis'. Raises RuntimeError if the tool is unavailable.
    """
    if tool == "trivy":
        findings, score = await trivy.run_trivy(target)
    elif tool == "lynis":
        findings, score = await lynis.run_lynis()
    else:
        raise ValueError(f"unknown posture tool '{tool}'")

    prev = await _previous_score(db, tool)
    drift = round(score - prev, 1) if prev is not None else 0.0

    run = PostureRun(
        tool=tool, score=score, drift=drift, findings=findings, total_findings=len(findings)
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run
