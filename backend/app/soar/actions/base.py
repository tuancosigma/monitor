"""Action interface, execution context, and registry.

An action is an async callable ``(params, ctx) -> ActionResult``. Dangerous actions
(external HTTP, script exec, closing incidents) are gated behind playbook ``auto_approve``
or an explicit confirmation, and are no-ops in dry-run mode.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ActionContext:
    """Shared state passed to every node in a playbook run."""

    db: AsyncSession
    trigger_type: str
    trigger: dict[str, Any]  # triggering alert/incident/webhook payload
    node_outputs: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False


@dataclass
class ActionResult:
    status: str  # ok, error, planned, skipped
    output: Any = None


ActionFn = Callable[[dict[str, Any], ActionContext], Awaitable[ActionResult]]

_REGISTRY: dict[str, ActionFn] = {}
_DANGEROUS: set[str] = set()


def register(name: str, *, dangerous: bool = False) -> Callable[[ActionFn], ActionFn]:
    def decorator(fn: ActionFn) -> ActionFn:
        _REGISTRY[name] = fn
        if dangerous:
            _DANGEROUS.add(name)
        return fn

    return decorator


def get_action(name: str) -> ActionFn | None:
    return _REGISTRY.get(name)


def is_dangerous(name: str) -> bool:
    return name in _DANGEROUS


def known_actions() -> list[str]:
    return sorted(_REGISTRY)
