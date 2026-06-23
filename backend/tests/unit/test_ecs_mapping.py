"""Unit tests for connector ECS-lite mapping (Wazuh, Prometheus, webhook-IN)."""

from __future__ import annotations

from app.connectors.prometheus import map_prometheus_sample
from app.connectors.wazuh import map_wazuh_alert
from app.connectors.webhook_in import map_webhook_payload
from app.ingest.validate import ValidationFailure, parse_event


def test_wazuh_alert_maps_to_ecs() -> None:
    alert = {
        "timestamp": "2026-06-24T01:00:00.000Z",
        "rule": {
            "level": 10,
            "description": "Multiple authentication failures",
            "mitre": {
                "id": ["T1110"],
                "tactic": ["Credential Access"],
                "technique": ["Brute Force"],
            },
        },
        "agent": {"name": "web-01", "ip": "10.0.0.5"},
        "data": {"srcip": "203.0.113.9", "srcuser": "root"},
    }
    ecs = map_wazuh_alert(alert)
    assert ecs["@timestamp"] == "2026-06-24T01:00:00.000Z"
    assert ecs["event.kind"] == "alert"
    assert ecs["event.severity"] == 70  # level 10 * 7
    assert ecs["host.name"] == "web-01"
    assert ecs["host.ip"] == ["10.0.0.5"]
    assert ecs["source.ip"] == "203.0.113.9"
    assert ecs["user.name"] == "root"
    assert ecs["threat.technique.id"] == "T1110"


def test_wazuh_mapping_is_defensive_on_missing_fields() -> None:
    ecs = map_wazuh_alert({"timestamp": "2026-06-24T01:00:00Z"})
    assert ecs["event.kind"] == "alert"
    assert "host.name" not in ecs  # omitted, not crashed


def test_wazuh_mapped_event_validates() -> None:
    import json

    ecs = map_wazuh_alert(
        {"timestamp": "2026-06-24T01:00:00Z", "rule": {"level": 5, "description": "x"},
         "agent": {"name": "h1"}}
    )
    result = parse_event(json.dumps(ecs))
    assert not isinstance(result, ValidationFailure)


def test_prometheus_sample_maps_to_metric_event() -> None:
    sample = {
        "metric": {"__name__": "node_cpu_seconds_total", "instance": "host:9100", "mode": "idle"},
        "value": [1_750_000_000, "1234.5"],
    }
    ecs = map_prometheus_sample("node_cpu_seconds_total", sample)
    assert ecs["event.kind"] == "metric"
    assert ecs["event.action"] == "node_cpu_seconds_total"
    assert ecs["host.name"] == "host:9100"
    assert ecs["labels"]["mode"] == "idle"
    assert ecs["labels"]["value"] == "1234.5"


def test_webhook_passthrough_when_no_mapping() -> None:
    ecs = map_webhook_payload({"@timestamp": "2026-06-24T01:00:00Z", "message": "hi"}, {})
    assert ecs["message"] == "hi"
    assert ecs["event.dataset"] == "webhook"


def test_webhook_mapping_resolves_dot_paths() -> None:
    payload = {"ts": "2026-06-24T01:00:00Z", "client": {"ip": "198.51.100.7"}, "msg": "denied"}
    mapping = {"@timestamp": "ts", "source.ip": "client.ip", "message": "msg"}
    ecs = map_webhook_payload(payload, mapping)
    assert ecs["@timestamp"] == "2026-06-24T01:00:00Z"
    assert ecs["source.ip"] == "198.51.100.7"
    assert ecs["message"] == "denied"


def test_webhook_always_sets_timestamp() -> None:
    ecs = map_webhook_payload({"foo": "bar"}, {"message": "missing.path"})
    assert "@timestamp" in ecs  # defaulted to now()
