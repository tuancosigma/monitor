"""Unit tests for Phase 0 health + metrics endpoints.

Dependency probes are monkeypatched so the test runs without a live stack.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_health() -> dict[str, object]:
        return {
            "status": "ok",
            "dependencies": [
                {"name": "clickhouse", "healthy": True, "detail": "Ok"},
                {"name": "redpanda", "healthy": True, "detail": "tcp ok"},
            ],
        }

    monkeypatch.setattr(main, "gather_health", fake_health)
    # Don't start the Kafka consumer / migrations against a non-existent stack.
    monkeypatch.setattr(main.settings, "ingest_enabled", False)
    return TestClient(main.app)


def test_healthz_ok(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    names = {d["name"] for d in body["dependencies"]}
    assert names == {"clickhouse", "redpanda"}


def test_metrics_prometheus(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    # Prometheus exposition always emits python GC/process metrics
    assert "python_info" in resp.text or "process_" in resp.text
