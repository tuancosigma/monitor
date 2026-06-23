"""Persist a playbook run as the audit record (trigger, per-node results, status)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook import PlaybookRun


async def record_run(
    db: AsyncSession,
    *,
    playbook_id: int,
    dry_run: bool,
    trigger_context: dict[str, Any],
    node_results: list[dict[str, Any]],
    status: str,
) -> PlaybookRun:
    run = PlaybookRun(
        playbook_id=playbook_id,
        status=status,
        dry_run=dry_run,
        trigger_context=trigger_context,
        node_results=node_results,
        node_count=len(node_results),
        finished_at=datetime.now(UTC),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run
