"""Content-hash response cache.

Key = sha256(task + model_family + content). A hit returns immediately and spends
no provider quota. In-memory TTL store (KISS) — swappable for Redis later.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass
class _Entry:
    value: str
    expires_at: float


class ResponseCache:
    def __init__(self, ttl_s: float = 3600.0) -> None:
        self._ttl = ttl_s
        self._store: dict[str, _Entry] = {}

    @staticmethod
    def make_key(task: str, model_family: str, content: str) -> str:
        digest = hashlib.sha256(f"{task}|{model_family}|{content}".encode()).hexdigest()
        return digest

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def put(self, key: str, value: str) -> None:
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self._ttl)


cache = ResponseCache()
