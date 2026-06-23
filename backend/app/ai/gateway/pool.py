"""Account pool + routing config loaded from ``config/ai_providers.yaml``.

An Account is one (provider, credential, bucket) tuple. Quota is per-org (Groq) /
per-project (Gemini), so each YAML account represents a distinct quota bucket.
The API key itself is resolved from the environment at load time, never stored in YAML.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.core.logging import get_logger

log = get_logger("sentinel.ai.pool")

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "ai_providers.yaml"


@dataclass
class Account:
    name: str
    provider: str
    base_url: str
    api_key: str
    models: list[str]
    rpm: int
    tpm: int
    rpd: int

    def supports(self, model: str) -> bool:
        return model in self.models


@dataclass
class GatewayConfig:
    accounts: list[Account] = field(default_factory=list)
    routing: dict[str, list[str]] = field(default_factory=dict)
    train_on_data_providers: set[str] = field(default_factory=set)

    def accounts_for(self, provider: str, model: str) -> list[Account]:
        return [a for a in self.accounts if a.provider == provider and a.supports(model)]


def load_config(path: Path | None = None) -> GatewayConfig:
    """Parse the YAML pool. Accounts whose api_key_env is unset are skipped (with a warning)."""
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        log.warning("ai_config_missing", path=str(cfg_path))
        return GatewayConfig()

    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    accounts: list[Account] = []
    for raw in data.get("accounts", []):
        api_key = os.environ.get(raw["api_key_env"], "")
        if not api_key:
            log.warning("ai_account_no_key", account=raw["name"], env=raw["api_key_env"])
            continue
        limits = raw.get("limits", {})
        accounts.append(
            Account(
                name=raw["name"],
                provider=raw["provider"],
                base_url=raw["base_url"],
                api_key=api_key,
                models=list(raw.get("models", [])),
                rpm=int(limits.get("rpm", 30)),
                tpm=int(limits.get("tpm", 10000)),
                rpd=int(limits.get("rpd", 1000)),
            )
        )

    return GatewayConfig(
        accounts=accounts,
        routing={k: list(v) for k, v in data.get("routing", {}).items()},
        train_on_data_providers=set(data.get("train_on_data_providers", [])),
    )
