"""Per-(account, model) rate tracking.

Local token buckets seeded from YAML limits give a best-effort pre-check, but the
runtime response headers (x-ratelimit-*, retry-after) are the source of truth: a
429 marks the account "cooling" until its reset time, and successful responses
refresh remaining counters from headers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    rpm: int
    tpm: int
    rpd: int
    # remaining counters (best-effort; corrected by headers)
    requests_today: int = 0
    minute_window_start: float = field(default_factory=time.monotonic)
    requests_this_minute: int = 0
    day_window_start: float = field(default_factory=time.monotonic)
    cooling_until: float = 0.0

    def _roll_windows(self, now: float) -> None:
        if now - self.minute_window_start >= 60:
            self.minute_window_start = now
            self.requests_this_minute = 0
        if now - self.day_window_start >= 86400:
            self.day_window_start = now
            self.requests_today = 0


class RateTracker:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], _Bucket] = {}

    def _bucket(self, account: str, model: str, rpm: int, tpm: int, rpd: int) -> _Bucket:
        key = (account, model)
        if key not in self._buckets:
            self._buckets[key] = _Bucket(rpm=rpm, tpm=tpm, rpd=rpd)
        return self._buckets[key]

    def allows(self, account: str, model: str, rpm: int, tpm: int, rpd: int) -> bool:
        """True if a call may proceed now (not cooling, within rpm/rpd windows)."""
        now = time.monotonic()
        b = self._bucket(account, model, rpm, tpm, rpd)
        if now < b.cooling_until:
            return False
        b._roll_windows(now)
        if b.requests_this_minute >= b.rpm:
            return False
        return b.requests_today < b.rpd

    def cooling_remaining(self, account: str, model: str, rpm: int, tpm: int, rpd: int) -> float:
        now = time.monotonic()
        b = self._bucket(account, model, rpm, tpm, rpd)
        return max(0.0, b.cooling_until - now)

    def rpd_remaining(self, account: str, model: str, rpm: int, tpm: int, rpd: int) -> int:
        b = self._bucket(account, model, rpm, tpm, rpd)
        b._roll_windows(time.monotonic())
        return max(0, b.rpd - b.requests_today)

    def record_request(self, account: str, model: str, rpm: int, tpm: int, rpd: int) -> None:
        now = time.monotonic()
        b = self._bucket(account, model, rpm, tpm, rpd)
        b._roll_windows(now)
        b.requests_this_minute += 1
        b.requests_today += 1

    def mark_cooling(self, account: str, model: str, retry_after_s: float,
                     rpm: int, tpm: int, rpd: int) -> None:
        b = self._bucket(account, model, rpm, tpm, rpd)
        b.cooling_until = time.monotonic() + max(0.0, retry_after_s)

    def update_from_headers(self, account: str, model: str, headers: dict[str, str],
                            rpm: int, tpm: int, rpd: int) -> None:
        """Correct counters from x-ratelimit-* headers when present (header = truth)."""
        b = self._bucket(account, model, rpm, tpm, rpd)
        remaining_day = headers.get("x-ratelimit-remaining-requests")
        if remaining_day is not None:
            try:
                b.requests_today = max(0, b.rpd - int(remaining_day))
            except ValueError:
                pass


tracker = RateTracker()
