"""Prometheus connector: poll the query API and map samples to ECS-lite metric events.

Each instant-vector sample becomes one ECS-lite event with event.kind=metric and the
Prometheus labels carried in the ECS ``labels`` map. Mapping is pure + unit-tested.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.connectors.base import ConnectorBase
from app.core.logging import get_logger
from app.core.ssrf_guard import get_safe_client

log = get_logger("sentinel.connectors.prometheus")


def map_prometheus_sample(query: str, sample: dict[str, Any]) -> dict[str, Any]:
    """Map one Prometheus instant-vector sample to an ECS-lite metric event."""
    metric = sample.get("metric", {}) or {}
    value = sample.get("value", [None, None])
    ts_unix, raw_val = [*value, None, None][:2]

    timestamp = (
        datetime.fromtimestamp(float(ts_unix), tz=UTC).isoformat()
        if ts_unix is not None
        else datetime.now(UTC).isoformat()
    )
    name = metric.get("__name__", query)
    labels = {k: str(v) for k, v in metric.items() if k != "__name__"}
    if raw_val is not None:
        labels["value"] = str(raw_val)

    ecs: dict[str, Any] = {
        "@timestamp": timestamp,
        "event.kind": "metric",
        "event.category": "host",
        "event.action": name,
        "event.dataset": "prometheus",
        "message": f"{name}={raw_val}",
        "observer.vendor": "Prometheus",
        "observer.product": "Prometheus",
        "labels": labels,
    }
    if metric.get("instance"):
        ecs["host.name"] = metric["instance"]
    return ecs


class PrometheusConnector(ConnectorBase):
    type = "prometheus"

    async def fetch(self, cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
        base = str(self.config["base_url"]).rstrip("/")
        queries = self.config.get("queries", [])
        if isinstance(queries, str):
            queries = [queries]

        events: list[dict[str, Any]] = []
        async with get_safe_client() as client:
            for query in queries:
                resp = await client.get(
                    f"{base}/api/v1/query", params={"query": query}, timeout=15.0
                )
                resp.raise_for_status()
                result = resp.json().get("data", {}).get("result", [])
                events.extend(map_prometheus_sample(query, s) for s in result)

        log.info("prometheus_polled", count=len(events))
        # Prometheus is stateless polling — no cursor needed.
        return events, cursor
