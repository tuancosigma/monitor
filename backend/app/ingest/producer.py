"""Kafka (Redpanda) producer for connectors and webhook-IN.

Connectors and the webhook-IN endpoint produce ECS-lite JSON to the same events
topic the P1 consumer reads, so all sources share one validate→ClickHouse path (DRY).
"""

from __future__ import annotations

import json
from typing import Any

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("sentinel.producer")


class EventProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        await self._producer.start()
        log.info("producer_started", topic=settings.kafka_events_topic)

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, event: dict[str, Any]) -> None:
        """Send one ECS-lite event dict to the events topic as JSON."""
        if self._producer is None:
            raise RuntimeError("producer not started")
        payload = json.dumps(event, default=str).encode("utf-8")
        await self._producer.send_and_wait(settings.kafka_events_topic, payload)

    async def publish_many(self, events: list[dict[str, Any]]) -> int:
        for event in events:
            await self.publish(event)
        return len(events)


producer = EventProducer()
