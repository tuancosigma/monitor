"""Shared resilience primitives: retry-with-backoff and a generic circuit breaker.

Used by connectors (and available to other outbound callers) so retry/backoff and
breaker behavior is not re-implemented per integration.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core.logging import get_logger

log = get_logger("sentinel.resilience")


async def retry_async[T](
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: float = 0.3,
) -> T:
    """Run ``fn`` with exponential backoff + jitter. Re-raises the last error."""
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await fn()
        except Exception as exc:  # caller decides what is retryable by raising/not
            last_exc = exc
            if attempt == attempts - 1:
                break
            delay = min(max_delay, base_delay * (2**attempt))
            delay += random.uniform(0, jitter * delay)  # noqa: S311 — jitter, not crypto
            log.warning("retry_backoff", attempt=attempt + 1, delay=round(delay, 2), error=str(exc))
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc


@dataclass
class _BreakerState:
    failures: int = 0
    open_until: float = 0.0


class CircuitBreaker:
    """Generic per-key circuit breaker (e.g. keyed by connector name)."""

    def __init__(self, threshold: int = 5, cooldown_s: float = 60.0) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_s
        self._states: dict[str, _BreakerState] = {}

    def is_open(self, key: str) -> bool:
        st = self._states.get(key)
        if st is None:
            return False
        if st.open_until and time.monotonic() < st.open_until:
            return True
        if st.open_until and time.monotonic() >= st.open_until:
            st.failures = 0
            st.open_until = 0.0
        return False

    def record_success(self, key: str) -> None:
        self._states[key] = _BreakerState()

    def record_failure(self, key: str) -> None:
        st = self._states.setdefault(key, _BreakerState())
        st.failures += 1
        if st.failures >= self._threshold:
            st.open_until = time.monotonic() + self._cooldown
            log.warning("circuit_open", key=key, cooldown_s=self._cooldown)
