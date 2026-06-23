"""In-process pub/sub hub feeding Server-Sent Events to the Explore live tail.

The ingest consumer publishes freshly-inserted events; each connected SSE client
holds a bounded queue. Slow clients drop oldest messages rather than blocking ingest.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.core.logging import get_logger

log = get_logger("sentinel.sse")

_MAX_QUEUE = 1000


class SseHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=_MAX_QUEUE)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._subscribers.discard(q)

    def publish(self, message: str) -> None:
        """Non-blocking fan-out. Drops the oldest item for any full subscriber queue."""
        for q in self._subscribers:
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(message)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


hub = SseHub()


async def event_stream(q: asyncio.Queue[str]) -> AsyncIterator[str]:
    """Yield SSE-framed messages; a periodic heartbeat keeps the connection alive."""
    try:
        while True:
            try:
                message = await asyncio.wait_for(q.get(), timeout=15.0)
                yield f"data: {message}\n\n"
            except TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        hub.unsubscribe(q)
