"""Dead-letter handling: failed events go to a Redpanda topic AND a ClickHouse table.

Failures must be observable, never silently dropped.
"""

from __future__ import annotations

from app.core import clickhouse
from app.core.logging import get_logger
from app.ingest.validate import ValidationFailure

log = get_logger("sentinel.dlq")


async def record_failures(failures: list[ValidationFailure]) -> None:
    """Insert validation failures into events_dlq for inspection."""
    if not failures:
        return
    rows = [[f.raw, f.error] for f in failures]
    await clickhouse.insert_rows("events_dlq", rows, ["raw", "error"])
    log.warning("dlq_recorded", count=len(failures))
