"""Validate a raw Kafka payload into an EcsEvent, or describe why it failed."""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from app.models.ecs_event import EcsEvent


@dataclass
class ValidationFailure:
    raw: str
    error: str


def parse_event(payload: bytes | str) -> EcsEvent | ValidationFailure:
    """Decode JSON + validate against EcsEvent. Never raises.

    The ``raw`` original payload is preserved on the event for forensic traceability.
    """
    raw_text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return ValidationFailure(raw=raw_text, error=f"json decode: {exc}")

    if not isinstance(data, dict):
        return ValidationFailure(raw=raw_text, error="payload is not a JSON object")

    data.setdefault("raw", raw_text)
    try:
        return EcsEvent.model_validate(data)
    except ValidationError as exc:
        return ValidationFailure(raw=raw_text, error=f"schema: {exc.errors()}")
