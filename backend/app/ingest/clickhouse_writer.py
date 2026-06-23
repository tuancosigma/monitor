"""Serialize EcsEvent -> ClickHouse row and batch-insert.

Column order is the single source of truth for both the ``events`` table layout
(migrations/001_events.sql) and the row vector built here. Keep them in sync.
"""

from __future__ import annotations

from typing import Any

from app.core import clickhouse
from app.models.ecs_event import EcsEvent

# Ordered (ClickHouse column, EcsEvent attribute). The timestamp column is the
# ECS dotted name; the rest are 1:1 with model attributes.
EVENT_COLUMNS: list[tuple[str, str]] = [
    ("@timestamp", "timestamp"),
    ("event_kind", "event_kind"),
    ("event_category", "event_category"),
    ("event_type", "event_type"),
    ("event_action", "event_action"),
    ("event_severity", "event_severity"),
    ("event_outcome", "event_outcome"),
    ("event_dataset", "event_dataset"),
    ("message", "message"),
    ("host_name", "host_name"),
    ("host_ip", "host_ip"),
    ("observer_vendor", "observer_vendor"),
    ("observer_product", "observer_product"),
    ("source_ip", "source_ip"),
    ("source_port", "source_port"),
    ("source_geo_country_iso_code", "source_geo_country_iso_code"),
    ("destination_ip", "destination_ip"),
    ("destination_port", "destination_port"),
    ("network_protocol", "network_protocol"),
    ("network_transport", "network_transport"),
    ("network_bytes", "network_bytes"),
    ("user_name", "user_name"),
    ("user_id", "user_id"),
    ("user_domain", "user_domain"),
    ("process_name", "process_name"),
    ("process_pid", "process_pid"),
    ("process_command_line", "process_command_line"),
    ("process_executable", "process_executable"),
    ("file_path", "file_path"),
    ("file_name", "file_name"),
    ("file_hash_sha256", "file_hash_sha256"),
    ("log_level", "log_level"),
    ("log_logger", "log_logger"),
    ("threat_tactic_name", "threat_tactic_name"),
    ("threat_technique_id", "threat_technique_id"),
    ("threat_technique_name", "threat_technique_name"),
    ("labels", "labels"),
    ("tags", "tags"),
    ("raw", "raw"),
]

COLUMN_NAMES: list[str] = [col for col, _ in EVENT_COLUMNS]

# Columns whose NULL must become a typed default (ClickHouse columns are non-nullable).
_STRING_DEFAULT = ""
_INT_DEFAULT = 0


def _coerce(attr: str, value: Any) -> Any:
    """Replace None with ClickHouse-compatible defaults; stringify enums."""
    if value is None:
        numeric = attr.endswith(("_port", "_pid", "_bytes", "_severity"))
        return _INT_DEFAULT if numeric else _STRING_DEFAULT
    if hasattr(value, "value"):  # StrEnum -> its string value
        return value.value
    return value


def event_to_row(event: EcsEvent) -> list[Any]:
    """Build a row vector matching COLUMN_NAMES order."""
    return [_coerce(attr, getattr(event, attr)) for _, attr in EVENT_COLUMNS]


async def write_batch(events: list[EcsEvent]) -> None:
    if not events:
        return
    rows = [event_to_row(e) for e in events]
    await clickhouse.insert_rows("events", rows, COLUMN_NAMES)
