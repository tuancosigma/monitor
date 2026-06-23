"""ConnectorManager: supervise enabled connectors as isolated polling tasks.

Each connector polls on an interval; on success the cursor + status persist, on failure
backoff applies and a per-connector circuit breaker can trip. A crashing connector is
isolated (its task restarts with backoff) and never takes down the app.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime

from sqlalchemy import select

from app.connectors.base import ConnectorBase
from app.connectors.prometheus import PrometheusConnector
from app.connectors.wazuh import WazuhConnector
from app.core.logging import get_logger
from app.core.metadata_db import AsyncSessionLocal
from app.core.resilience import CircuitBreaker
from app.ingest.producer import producer
from app.models.connector import Connector

log = get_logger("sentinel.connectors.manager")

# Registry: connector type -> implementation class (polled connectors only).
REGISTRY: dict[str, type[ConnectorBase]] = {
    "wazuh": WazuhConnector,
    "prometheus": PrometheusConnector,
}

# Push-based sources (webhook-IN) are not polled by the manager.
PUSH_TYPES = {"webhook"}

_POLL_INTERVAL_S = 30.0


class ConnectorManager:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._breaker = CircuitBreaker(threshold=5, cooldown_s=120.0)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._supervise(), name="connector-manager")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _supervise(self) -> None:
        log.info("connector_manager_started")
        while self._running:
            try:
                await self._poll_all()
            except Exception as exc:  # supervisor must never die
                log.error("connector_supervise_error", error=str(exc))
            await asyncio.sleep(_POLL_INTERVAL_S)

    async def _poll_all(self) -> None:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(select(Connector).where(Connector.is_active.is_(True)))
            ).scalars().all()
            for row in rows:
                if self._breaker.is_open(row.name):
                    continue
                await self._poll_one(row.id)

    async def _poll_one(self, connector_id: int) -> None:
        async with AsyncSessionLocal() as session:
            row = await session.get(Connector, connector_id)
            if row is None:
                return
            if row.type in PUSH_TYPES:
                return  # webhook-IN is push-based, not polled
            impl_cls = REGISTRY.get(row.type)
            if impl_cls is None:
                log.warning("connector_unknown_type", type=row.type)
                return

            connector = impl_cls(row.name, dict(row.config))
            try:
                events, new_cursor = await connector.fetch(row.cursor)
                if events:
                    await producer.publish_many(events)
                # Persist cursor + status only after a successful emit (avoid dup/loss).
                row.cursor = new_cursor
                row.status = "running"
                row.last_error = None
                row.last_run_at = datetime.now(UTC)
                await session.commit()
                self._breaker.record_success(row.name)
            except Exception as exc:
                row.status = "error"
                row.last_error = str(exc)[:1024]
                await session.commit()
                self._breaker.record_failure(row.name)
                log.warning("connector_poll_failed", connector=row.name, error=str(exc))


manager = ConnectorManager()
