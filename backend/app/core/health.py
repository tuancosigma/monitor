"""Dependency health probes for ``/healthz``.

Pings stateful dependencies (ClickHouse, Redpanda) without raising, returning a
structured status so the endpoint can report partial degradation.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass
class DependencyStatus:
    name: str
    healthy: bool
    detail: str


async def _check_clickhouse() -> DependencyStatus:
    url = f"http://{settings.clickhouse_host}:{settings.clickhouse_port}/ping"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
        ok = resp.status_code == 200
        return DependencyStatus("clickhouse", ok, "Ok" if ok else f"status {resp.status_code}")
    except Exception as exc:  # health probe must never raise
        return DependencyStatus("clickhouse", False, str(exc))


async def _check_redpanda() -> DependencyStatus:
    host, _, port_s = settings.kafka_bootstrap_servers.partition(":")
    port = int(port_s or "9092")
    try:
        fut = asyncio.open_connection(host, port)
        _, writer = await asyncio.wait_for(fut, timeout=2.0)
        writer.close()
        return DependencyStatus("redpanda", True, "tcp ok")
    except (OSError, TimeoutError, socket.gaierror) as exc:
        return DependencyStatus("redpanda", False, str(exc))


async def gather_health() -> dict[str, object]:
    """Run all dependency probes concurrently and aggregate the result."""
    deps = await asyncio.gather(_check_clickhouse(), _check_redpanda())
    healthy = all(d.healthy for d in deps)
    return {
        "status": "ok" if healthy else "degraded",
        "dependencies": [
            {"name": d.name, "healthy": d.healthy, "detail": d.detail} for d in deps
        ],
    }
