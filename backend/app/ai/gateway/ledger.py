"""Token usage ledger → Prometheus /metrics + in-memory rows for /ai/usage."""

from __future__ import annotations

from dataclasses import dataclass, field

from prometheus_client import Counter

TOKENS_IN = Counter(
    "sentinel_ai_tokens_in_total", "Prompt tokens", ["provider", "account", "task"]
)
TOKENS_OUT = Counter(
    "sentinel_ai_tokens_out_total", "Completion tokens", ["provider", "account", "task"]
)
CALLS = Counter(
    "sentinel_ai_calls_total", "Gateway calls", ["provider", "account", "task", "outcome"]
)


@dataclass
class UsageRow:
    provider: str
    account: str
    task: str
    tokens_in: int = 0
    tokens_out: int = 0
    calls: int = 0


@dataclass
class Ledger:
    _rows: dict[tuple[str, str, str], UsageRow] = field(default_factory=dict)

    def record(self, provider: str, account: str, task: str,
               tokens_in: int, tokens_out: int, outcome: str = "ok") -> None:
        key = (provider, account, task)
        row = self._rows.setdefault(key, UsageRow(provider, account, task))
        row.tokens_in += tokens_in
        row.tokens_out += tokens_out
        row.calls += 1
        TOKENS_IN.labels(provider, account, task).inc(tokens_in)
        TOKENS_OUT.labels(provider, account, task).inc(tokens_out)
        CALLS.labels(provider, account, task, outcome).inc()

    def rows(self) -> list[UsageRow]:
        return list(self._rows.values())


ledger = Ledger()
