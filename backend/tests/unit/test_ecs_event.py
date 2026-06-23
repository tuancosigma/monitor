"""Unit tests for ECS-lite parsing/validation and row serialization."""

from __future__ import annotations

from datetime import UTC

from app.ingest.clickhouse_writer import COLUMN_NAMES, event_to_row
from app.ingest.validate import ValidationFailure, parse_event
from app.models.ecs_event import EcsEvent, EventKind, EventOutcome


def test_parse_valid_ecs_dotted_keys() -> None:
    payload = (
        '{"@timestamp":"2026-06-23T10:00:00Z","event.category":"authentication",'
        '"event.action":"ssh_login_failed","event.severity":70,"event.outcome":"failure",'
        '"host.name":"web-01","source.ip":"10.0.0.5","user.name":"root"}'
    )
    event = parse_event(payload)
    assert isinstance(event, EcsEvent)
    assert event.event_action == "ssh_login_failed"
    assert event.event_severity == 70
    assert event.event_outcome is EventOutcome.failure
    assert event.host_name == "web-01"
    assert event.timestamp.tzinfo == UTC
    # raw payload preserved for forensics
    assert event.raw is not None and "ssh_login_failed" in event.raw


def test_parse_invalid_json() -> None:
    result = parse_event("{not json")
    assert isinstance(result, ValidationFailure)
    assert "json decode" in result.error


def test_parse_missing_required_timestamp() -> None:
    result = parse_event('{"message":"no timestamp"}')
    assert isinstance(result, ValidationFailure)
    assert "schema" in result.error


def test_parse_severity_out_of_range() -> None:
    result = parse_event('{"@timestamp":"2026-06-23T10:00:00Z","event.severity":250}')
    assert isinstance(result, ValidationFailure)


def test_naive_timestamp_coerced_to_utc() -> None:
    event = parse_event('{"@timestamp":"2026-06-23T10:00:00"}')
    assert isinstance(event, EcsEvent)
    assert event.timestamp.tzinfo == UTC


def test_event_to_row_matches_columns() -> None:
    event = parse_event('{"@timestamp":"2026-06-23T10:00:00Z","host.name":"h1"}')
    assert isinstance(event, EcsEvent)
    row = event_to_row(event)
    assert len(row) == len(COLUMN_NAMES)
    # None defaults coerced: ports/pids -> 0, strings -> ""
    idx_port = COLUMN_NAMES.index("source_port")
    assert row[idx_port] == 0
    idx_kind = COLUMN_NAMES.index("event_kind")
    assert row[idx_kind] == EventKind.event.value
