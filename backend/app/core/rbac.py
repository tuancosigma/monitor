"""Role-based access control guards (admin > analyst > viewer).

Roles are carried in the ``X-Sentinel-Role`` header (a full JWT issuer is out of MVP
scope). Enforcement is gated by ``settings.rbac_enabled`` so the dev UI keeps working
without auth wiring; when enabled, ``require_role`` returns a FastAPI dependency that
rejects insufficient roles with 403.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Header, HTTPException, status

from app.core.config import settings

ROLE_LEVELS: dict[str, int] = {"viewer": 1, "analyst": 2, "admin": 3}


def role_level(role: str | None) -> int:
    return ROLE_LEVELS.get((role or "").lower(), 0)


def require_role(minimum: str) -> Callable[..., Coroutine[Any, Any, str]]:
    """Build a dependency that requires at least ``minimum`` role when RBAC is enabled."""
    needed = ROLE_LEVELS[minimum]

    async def dependency(
        x_sentinel_role: str | None = Header(default=None),
    ) -> str:
        if not settings.rbac_enabled:
            return x_sentinel_role or "admin"  # dev: unauthenticated acts as admin
        if role_level(x_sentinel_role) < needed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"requires '{minimum}' role or higher",
            )
        return x_sentinel_role or ""

    return dependency
