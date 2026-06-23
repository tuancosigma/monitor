"""Kafka (Redpanda) ingest consumer.

Pulls batches from the events topic, validates each message, batch-inserts valid
EcsEvents into ClickHouse, dead-letters the rest, and fans inserted rows out to SSE.
Runs as a background asyncio task started from the app lifespan.

Hot-path rule: NO LLM calls here — pure deterministic validation + persistence.
"""

from __future__ import annotations

import asyncio
import contextlib

from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Gauge

from app.core.config import settings
from app.core.logging import get_logger
from app.ingest import clickhouse_writer, dlq
from app.ingest.validate import ValidationFailure, parse_event
from app.realtime.sse import hub

log = get_logger("sentinel.consumer")

INGESTED = Counter("sentinel_events_ingested_total", "Events validated + written")
FAILED = Counter("sentinel_events_dlq_total", "Events sent to dead-letter")
LAG = Gauge("sentinel_consumer_batch_size", "Size of the last processed batch")

_BATCH_MAX = 5000
_BATCH_WINDOW_S = 0.5


class IngestConsumer:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="ingest-consumer")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        consumer = AIOKafkaConsumer(
            settings.kafka_events_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id="sentinel-ingest",
            enable_auto_commit=True,
            auto_offset_reset="latest",
        )
        await consumer.start()
        log.info("consumer_started", topic=settings.kafka_events_topic)
        try:
            while self._running:
                batch = await consumer.getmany(timeout_ms=int(_BATCH_WINDOW_S * 1000),
                                                max_records=_BATCH_MAX)
                messages = [m for records in batch.values() for m in records]
                if messages:
                    await self._process([m.value for m in messages])
        finally:
            await consumer.stop()
            log.info("consumer_stopped")

    async def _process(self, payloads: list[bytes]) -> None:
        valid = []
        failures: list[ValidationFailure] = []
        for payload in payloads:
            result = parse_event(payload)
            if isinstance(result, ValidationFailure):
                failures.append(result)
            else:
                valid.append(result)

        LAG.set(len(payloads))
        if valid:
            await clickhouse_writer.write_batch(valid)
            INGESTED.inc(len(valid))
            for event in valid:
                hub.publish(event.model_dump_json(by_alias=True))
        if failures:
            await dlq.record_failures(failures)
            FAILED.inc(len(failures))


consumer = IngestConsumer()
