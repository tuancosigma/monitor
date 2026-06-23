"""ECS-lite event model — the cross-phase data contract.

Mirrors ``schema/ecs_lite.md`` (Appendix A). Every log/metric/alert is normalized
to this shape before being written to ClickHouse. Missing fields default to None.

Field names use ECS dotted paths via aliases (e.g. ``event.kind``) but flatten to
snake_case attributes that map 1:1 onto ClickHouse columns (see clickhouse_writer).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventKind(StrEnum):
    event = "event"
    alert = "alert"
    metric = "metric"
    state = "state"
    signal = "signal"


class EventCategory(StrEnum):
    authentication = "authentication"
    network = "network"
    process = "process"
    file = "file"
    malware = "malware"
    intrusion_detection = "intrusion_detection"
    web = "web"
    host = "host"
    configuration = "configuration"


class EventType(StrEnum):
    start = "start"
    end = "end"
    info = "info"
    error = "error"
    connection = "connection"
    access = "access"
    change = "change"
    denied = "denied"
    allowed = "allowed"


class EventOutcome(StrEnum):
    success = "success"
    failure = "failure"
    unknown = "unknown"


class EcsEvent(BaseModel):
    """Normalized event. Accepts ECS dotted keys (alias) or snake_case (field name)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    timestamp: datetime = Field(alias="@timestamp")

    event_kind: EventKind = Field(default=EventKind.event, alias="event.kind")
    event_category: EventCategory | None = Field(default=None, alias="event.category")
    event_type: EventType | None = Field(default=None, alias="event.type")
    event_action: str | None = Field(default=None, alias="event.action")
    event_severity: int = Field(default=0, ge=0, le=100, alias="event.severity")
    event_outcome: EventOutcome = Field(default=EventOutcome.unknown, alias="event.outcome")
    event_dataset: str | None = Field(default=None, alias="event.dataset")
    message: str | None = None

    host_name: str | None = Field(default=None, alias="host.name")
    host_ip: list[str] = Field(default_factory=list, alias="host.ip")
    observer_vendor: str | None = Field(default=None, alias="observer.vendor")
    observer_product: str | None = Field(default=None, alias="observer.product")

    source_ip: str | None = Field(default=None, alias="source.ip")
    source_port: int | None = Field(default=None, alias="source.port")
    source_geo_country_iso_code: str | None = Field(
        default=None, alias="source.geo.country_iso_code"
    )
    destination_ip: str | None = Field(default=None, alias="destination.ip")
    destination_port: int | None = Field(default=None, alias="destination.port")
    network_protocol: str | None = Field(default=None, alias="network.protocol")
    network_transport: str | None = Field(default=None, alias="network.transport")
    network_bytes: int | None = Field(default=None, alias="network.bytes")

    user_name: str | None = Field(default=None, alias="user.name")
    user_id: str | None = Field(default=None, alias="user.id")
    user_domain: str | None = Field(default=None, alias="user.domain")
    process_name: str | None = Field(default=None, alias="process.name")
    process_pid: int | None = Field(default=None, alias="process.pid")
    process_command_line: str | None = Field(default=None, alias="process.command_line")
    process_executable: str | None = Field(default=None, alias="process.executable")
    file_path: str | None = Field(default=None, alias="file.path")
    file_name: str | None = Field(default=None, alias="file.name")
    file_hash_sha256: str | None = Field(default=None, alias="file.hash.sha256")

    log_level: str | None = Field(default=None, alias="log.level")
    log_logger: str | None = Field(default=None, alias="log.logger")

    threat_tactic_name: str | None = Field(default=None, alias="threat.tactic.name")
    threat_technique_id: str | None = Field(default=None, alias="threat.technique.id")
    threat_technique_name: str | None = Field(default=None, alias="threat.technique.name")

    labels: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    raw: str | None = None

    @field_validator("timestamp")
    @classmethod
    def _ensure_utc(cls, value: datetime) -> datetime:
        """Coerce naive datetimes to UTC; convert aware ones to UTC."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
