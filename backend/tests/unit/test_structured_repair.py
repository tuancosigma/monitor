"""Unit tests for structured JSON output: validation, repair-retry, cache."""

from __future__ import annotations

import pytest

from app.ai.gateway import breaker as breaker_mod
from app.ai.gateway import rate_tracker as rt_mod
from app.ai.gateway.cache import cache
from app.ai.gateway.client import CallResult
from app.ai.gateway.pool import Account, GatewayConfig
from app.ai.gateway.structured import StructuredOutputError, generate_json

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["x"],
    "properties": {"x": {"type": "number"}},
}


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    rt_mod.tracker._buckets.clear()
    breaker_mod.breaker._states.clear()
    cache._store.clear()


def _config() -> GatewayConfig:
    acct = Account("groq-1", "groq", "http://groq", "k", ["m"], 30, 12000, 1000)
    return GatewayConfig(accounts=[acct], routing={"triage": ["groq:m"]})


async def test_valid_json_passes_first_try() -> None:
    async def fake_call(account: Account, model: str, messages: list[dict[str, str]],
                        *, json_object: bool = False) -> CallResult:
        return CallResult(content='{"x": 42}')

    out = await generate_json("triage", "sys", "uniq-content-1", _SCHEMA,
                              config=_config(), call_fn=fake_call)
    assert out == {"x": 42}


async def test_bad_json_then_repair_succeeds() -> None:
    attempts = {"n": 0}

    async def fake_call(account: Account, model: str, messages: list[dict[str, str]],
                        *, json_object: bool = False) -> CallResult:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return CallResult(content="not json at all")
        return CallResult(content='```json\n{"x": 7}\n```')  # fenced, still parsed

    out = await generate_json("triage", "sys", "uniq-content-2", _SCHEMA,
                              config=_config(), call_fn=fake_call)
    assert out == {"x": 7}
    assert attempts["n"] == 2  # one repair-retry happened


async def test_schema_violation_after_repair_raises() -> None:
    async def fake_call(account: Account, model: str, messages: list[dict[str, str]],
                        *, json_object: bool = False) -> CallResult:
        return CallResult(content='{"x": "not a number"}')

    with pytest.raises(StructuredOutputError):
        await generate_json("triage", "sys", "uniq-content-3", _SCHEMA,
                            config=_config(), call_fn=fake_call)


async def test_cache_hit_skips_call() -> None:
    calls = {"n": 0}

    async def fake_call(account: Account, model: str, messages: list[dict[str, str]],
                        *, json_object: bool = False) -> CallResult:
        calls["n"] += 1
        return CallResult(content='{"x": 1}')

    cfg = _config()
    await generate_json("triage", "sys", "same", _SCHEMA, config=cfg, call_fn=fake_call)
    await generate_json("triage", "sys", "same", _SCHEMA, config=cfg, call_fn=fake_call)
    assert calls["n"] == 1  # second call served from cache
