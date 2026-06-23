"""Unit tests for gateway routing: 429 rotation, privacy policy, NoCapacity."""

from __future__ import annotations

import pytest

from app.ai.gateway import breaker as breaker_mod
from app.ai.gateway import rate_tracker as rt_mod
from app.ai.gateway.client import CallResult, RateLimited
from app.ai.gateway.pool import Account, GatewayConfig
from app.ai.gateway.router import NoCapacity, route


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    rt_mod.tracker._buckets.clear()
    breaker_mod.breaker._states.clear()


def _config() -> GatewayConfig:
    groq = Account("groq-1", "groq", "http://groq", "k", ["m-groq"], 30, 12000, 1000)
    gemini = Account("gemini-1", "gemini", "http://gem", "k", ["m-gem"], 15, 250000, 1500)
    return GatewayConfig(
        accounts=[groq, gemini],
        routing={"triage": ["groq:m-groq", "gemini:m-gem"]},
        train_on_data_providers={"gemini"},
    )


async def test_rotates_to_next_provider_on_429() -> None:
    calls: list[str] = []

    async def fake_call(account: Account, model: str, messages: list[dict[str, str]],
                        *, json_object: bool = False) -> CallResult:
        calls.append(account.name)
        if account.provider == "groq":
            raise RateLimited(retry_after=5.0)
        return CallResult(content='{"ok":true}', tokens_in=10, tokens_out=5)

    account, _model, result = await route(
        "triage", [{"role": "user", "content": "x"}], config=_config(), call_fn=fake_call
    )
    assert account.name == "gemini-1"
    assert result.content == '{"ok":true}'
    assert calls == ["groq-1", "gemini-1"]  # tried groq, fell through to gemini


async def test_sensitive_excludes_gemini_free() -> None:
    async def fake_call(account: Account, model: str, messages: list[dict[str, str]],
                        *, json_object: bool = False) -> CallResult:
        if account.provider == "groq":
            raise RateLimited(retry_after=5.0)
        return CallResult(content="{}")  # gemini would succeed, but must be skipped

    # groq 429 + gemini forbidden for sensitive => NoCapacity (never leaks to gemini).
    with pytest.raises(NoCapacity):
        await route(
            "triage", [{"role": "user", "content": "secret"}],
            sensitive=True, config=_config(), call_fn=fake_call,
        )


async def test_success_records_ledger_and_returns_first_account() -> None:
    async def fake_call(account: Account, model: str, messages: list[dict[str, str]],
                        *, json_object: bool = False) -> CallResult:
        return CallResult(content="{}", tokens_in=3, tokens_out=2)

    account, _, _ = await route(
        "triage", [{"role": "user", "content": "x"}], config=_config(), call_fn=fake_call
    )
    assert account.name == "groq-1"
