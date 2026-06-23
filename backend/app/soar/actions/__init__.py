"""SOAR actions: registry of named action handlers used by playbook nodes."""

from app.soar.actions import builtin  # noqa: F401 — registers built-in actions on import
from app.soar.actions.base import (
    ActionContext,
    ActionResult,
    get_action,
    is_dangerous,
)

__all__ = ["ActionContext", "ActionResult", "get_action", "is_dangerous"]
