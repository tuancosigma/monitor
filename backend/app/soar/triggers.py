"""Playbook triggers: match bound playbooks to events and execute them.

Event-driven triggers (alert/incident/webhook) are fired by the producing subsystem via
``fire``. Cron playbooks are evaluated by a lightweight background worker on an interval.
Dangerous actions stay gated unless a playbook is ``auto_approve``.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.core.metadata_db import AsyncSessionLocal
from app.models.playbook import Playbook
from app.soar.executor import execute_playbook

log = get_logger("sentinel.soar.triggers")


def match_filter(trigger_filter: dict[str, Any], trigger: dict[str, Any]) -> bool:
    """Shallow subset match: every key in the filter must equal the trigger's value."""
    return all(trigger.get(k) == v for k, v in trigger_filter.items())


async def fire(trigger_type: str, trigger: dict[str, Any]) -> int:
    """Run every active playbook bound to this trigger whose filter matches.

    Returns the number of playbooks executed. Each runs in its own session; one failing
    playbook never blocks the others.
    """
    fired = 0
    async with AsyncSessionLocal() as session:
        playbooks = (
            await session.execute(
                select(Playbook).where(
                    Playbook.trigger_type == trigger_type,
                    Playbook.is_active.is_(True),
                )
            )
        ).scalars().all()

    for pb in playbooks:
        if not match_filter(pb.trigger_filter, trigger):
            continue
        try:
            async with AsyncSessionLocal() as run_session:
                pb_local = await run_session.get(Playbook, pb.id)
                if pb_local is not None:
                    await execute_playbook(run_session, pb_local, trigger_type, trigger)
                    fired += 1
        except Exception as exc:
            log.error("soar_trigger_failed", playbook=pb.name, error=str(exc))
    return fired


# --- cron worker -----------------------------------------------------------

_cron_task: asyncio.Task[None] | None = None
_running = False
_last_fired: dict[int, float] = {}


async def _cron_loop() -> None:
    log.info("soar_cron_started")
    while _running:
        try:
            await _evaluate_cron()
        except Exception as exc:  # worker must never die
            log.error("soar_cron_error", error=str(exc))
        await asyncio.sleep(30)


async def _evaluate_cron() -> None:
    now = time.monotonic()
    async with AsyncSessionLocal() as session:
        playbooks = (
            await session.execute(
                select(Playbook).where(
                    Playbook.trigger_type == "cron",
                    Playbook.is_active.is_(True),
                )
            )
        ).scalars().all()
        bindings = [(p.id, int(p.trigger_filter.get("interval_seconds", 300))) for p in playbooks]

    for playbook_id, interval in bindings:
        last = _last_fired.get(playbook_id, 0.0)
        if now - last >= interval:
            _last_fired[playbook_id] = now
            await fire_one(playbook_id)


async def fire_one(playbook_id: int) -> None:
    async with AsyncSessionLocal() as session:
        pb = await session.get(Playbook, playbook_id)
        if pb is not None:
            await execute_playbook(session, pb, "cron", {"type": "cron"})


def start_cron_worker() -> None:
    global _cron_task, _running
    if _running:
        return
    _running = True
    _cron_task = asyncio.create_task(_cron_loop(), name="soar-cron")


async def stop_cron_worker() -> None:
    global _running
    _running = False
    if _cron_task is not None:
        _cron_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _cron_task
