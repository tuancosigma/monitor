"""Per-provider circuit breaker.

Consecutive provider errors open the circuit for a cooldown, during which the
router skips that provider entirely (independent of per-account rate limits).
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _State:
    failures: int = 0
    open_until: float = 0.0


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown_s: float = 30.0) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_s
        self._states: dict[str, _State] = {}

    def is_open(self, provider: str) -> bool:
        st = self._states.get(provider)
        if st is None:
            return False
        if st.open_until and time.monotonic() < st.open_until:
            return True
        if st.open_until and time.monotonic() >= st.open_until:
            # cooldown elapsed — half-open: reset and allow a trial
            st.failures = 0
            st.open_until = 0.0
        return False

    def record_success(self, provider: str) -> None:
        self._states[provider] = _State()

    def record_failure(self, provider: str) -> None:
        st = self._states.setdefault(provider, _State())
        st.failures += 1
        if st.failures >= self._threshold:
            st.open_until = time.monotonic() + self._cooldown


breaker = CircuitBreaker()
