"""Webhook-IN mapping: turn arbitrary external JSON into an ECS-lite event.

A webhook source is a Connector row of type "webhook" with config:
  { "token": "${WEBHOOK_TOKEN}", "mapping": {"<ecs.field>": "<dot.path.in.payload>"} }
If no mapping is given and the payload already looks ECS-lite (has @timestamp), it is
passed through. Mapping is pure and unit-tested.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _resolve_path(payload: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path (e.g. 'client.ip') against the payload."""
    node: Any = payload
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def map_webhook_payload(payload: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """Build an ECS-lite event from an external payload using a field mapping.

    Always sets @timestamp (now() if not mapped/present) so downstream validation passes.
    """
    if not mapping:
        ecs = dict(payload)  # assume already ECS-lite-ish
    else:
        ecs = {ecs_field: _resolve_path(payload, src) for ecs_field, src in mapping.items()}
        ecs = {k: v for k, v in ecs.items() if v is not None}

    ecs.setdefault("@timestamp", datetime.now(UTC).isoformat())
    ecs.setdefault("event.kind", "event")
    ecs.setdefault("event.dataset", "webhook")
    ecs.setdefault("observer.product", "Sentinel")
    return ecs
