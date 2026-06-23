"""Structured JSON generation: schema injection, validation, one repair-retry, cache.

Wraps the router. The JSON schema is injected into the system prompt and
``response_format=json_object`` is requested; the response is parsed and validated
with jsonschema. On parse/validation failure, exactly one repair-retry is attempted
with an explicit "return valid JSON only" instruction before giving up.
"""

from __future__ import annotations

import json
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaValidationError

from app.ai.gateway import router as router_mod
from app.ai.gateway.cache import cache
from app.ai.gateway.pool import GatewayConfig
from app.ai.gateway.router import CallFn
from app.core.logging import get_logger

log = get_logger("sentinel.ai.structured")


class StructuredOutputError(Exception):
    """Model could not produce schema-valid JSON even after a repair-retry."""


def _build_system(base_system: str, schema: dict[str, Any]) -> str:
    return (
        f"{base_system}\n\n"
        "Return ONLY a single JSON object that validates against this JSON schema. "
        "No markdown, no prose outside the JSON.\n"
        f"JSON schema:\n{json.dumps(schema)}"
    )


def _parse_and_validate(text: str, schema: dict[str, Any]) -> dict[str, Any]:
    # Tolerate accidental ```json fences.
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON is not an object")
    Draft202012Validator(schema).validate(data)
    return data


async def generate_json(
    task: str,
    base_system: str,
    user_content: str,
    schema: dict[str, Any],
    *,
    sensitive: bool = False,
    cache_key: str | None = None,
    config: GatewayConfig | None = None,
    call_fn: CallFn | None = None,
) -> dict[str, Any]:
    model_family = task
    key = cache_key or cache.make_key(task, model_family, user_content)
    cached = cache.get(key)
    if cached is not None:
        return cast(dict[str, Any], json.loads(cached))

    system = _build_system(base_system, schema)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    _, _, result = await router_mod.route(
        task, messages, sensitive=sensitive, json_object=True, config=config, call_fn=call_fn
    )

    try:
        data = _parse_and_validate(result.content, schema)
    except (json.JSONDecodeError, ValueError, SchemaValidationError) as first_err:
        log.warning("ai_json_repair_attempt", task=task, error=str(first_err))
        repair_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": result.content},
            {
                "role": "user",
                "content": "Your previous reply was not valid per the schema. "
                "Return ONLY the corrected JSON object, nothing else.",
            },
        ]
        _, _, repaired = await router_mod.route(
            task, repair_messages, sensitive=sensitive, json_object=True,
            config=config, call_fn=call_fn,
        )
        try:
            data = _parse_and_validate(repaired.content, schema)
        except (json.JSONDecodeError, ValueError, SchemaValidationError) as second_err:
            raise StructuredOutputError(str(second_err)) from second_err

    cache.put(key, json.dumps(data))
    return data
