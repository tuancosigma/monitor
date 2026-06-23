"""Routing + account selection (Appendix B algorithm).

For a task, walk its routing chain (provider:model). For each, skip providers with
an open circuit or — when the task is sensitive — providers whose free tier may train
on data. Within a provider, try accounts ordered by (not cooling, most RPD left).
Honor 429 (cool the account) and provider errors (trip the breaker), then fall through
to the next option. Raise NoCapacity only when every option is exhausted.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.ai.gateway import client as client_mod
from app.ai.gateway.breaker import breaker
from app.ai.gateway.client import CallResult, ProviderError, RateLimited
from app.ai.gateway.ledger import ledger
from app.ai.gateway.pool import Account, GatewayConfig, load_config
from app.ai.gateway.rate_tracker import tracker
from app.core.logging import get_logger

log = get_logger("sentinel.ai.router")

CallFn = Callable[..., Awaitable[CallResult]]

_config: GatewayConfig | None = None


class NoCapacity(Exception):
    """Every provider/account in the task chain is unavailable."""


def get_config() -> GatewayConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    global _config
    _config = None


async def route(
    task: str,
    messages: list[dict[str, str]],
    *,
    sensitive: bool = False,
    json_object: bool = False,
    config: GatewayConfig | None = None,
    call_fn: CallFn | None = None,
) -> tuple[Account, str, CallResult]:
    cfg = config or get_config()
    call = call_fn or client_mod.call_account
    chain = cfg.routing.get(task, [])
    if not chain:
        raise NoCapacity(f"no routing chain for task '{task}'")

    for entry in chain:
        provider, _, model = entry.partition(":")
        # Privacy policy: never send sensitive data to a free tier that may train on it.
        if sensitive and provider in cfg.train_on_data_providers:
            continue
        if breaker.is_open(provider):
            continue

        accounts = cfg.accounts_for(provider, model)
        accounts.sort(
            key=lambda a: (
                tracker.cooling_remaining(a.name, model, a.rpm, a.tpm, a.rpd) > 0,
                -tracker.rpd_remaining(a.name, model, a.rpm, a.tpm, a.rpd),
            )
        )

        for account in accounts:
            if not tracker.allows(account.name, model, account.rpm, account.tpm, account.rpd):
                continue
            try:
                result = await call(account, model, messages, json_object=json_object)
            except RateLimited as err:
                tracker.mark_cooling(
                    account.name, model, err.retry_after,
                    account.rpm, account.tpm, account.rpd,
                )
                ledger.record(provider, account.name, task, 0, 0, outcome="rate_limited")
                log.warning("ai_account_cooling", account=account.name, retry_after=err.retry_after)
                continue
            except ProviderError as err:
                breaker.record_failure(provider)
                ledger.record(provider, account.name, task, 0, 0, outcome="error")
                log.warning("ai_provider_error", provider=provider, error=str(err))
                continue

            tracker.record_request(account.name, model, account.rpm, account.tpm, account.rpd)
            tracker.update_from_headers(
                account.name, model, result.headers, account.rpm, account.tpm, account.rpd
            )
            breaker.record_success(provider)
            ledger.record(provider, account.name, task, result.tokens_in, result.tokens_out)
            return account, model, result

    raise NoCapacity(f"all providers exhausted for task '{task}'")
