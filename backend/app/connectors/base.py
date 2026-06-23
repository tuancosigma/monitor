"""Connector base interface.

A connector authenticates, polls an upstream since a cursor, and maps the response
to ECS-lite event dicts. The manager owns the loop, retry/backoff, breaker, emit, and
cursor persistence — connectors stay focused on fetch + mapping.

Config secrets are env-references like ``${WAZUH_KEY}``, resolved at construction.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any

_ENV_REF = re.compile(r"\$\{([^}]+)\}")


def resolve_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Replace ${VAR} references in string values with environment values."""
    out: dict[str, Any] = {}
    for k, v in config.items():
        if isinstance(v, str):
            out[k] = _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), v)
        else:
            out[k] = v
    return out


class ConnectorBase(ABC):
    """Abstract connector. Subclasses implement ``fetch`` and ``map_to_ecs``."""

    type: str = "base"

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = resolve_secrets(config)

    @abstractmethod
    async def fetch(self, cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
        """Poll the upstream since ``cursor``; return (ecs_lite_events, new_cursor).

        Must raise on transport/auth errors so the manager can apply backoff + breaker.
        """
        raise NotImplementedError
