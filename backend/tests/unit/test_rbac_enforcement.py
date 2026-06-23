"""Unit tests for RBAC role guards."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core import rbac
from app.core.config import settings


@pytest.fixture(autouse=True)
def _enable_rbac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rbac_enabled", True)


async def test_viewer_denied_on_admin_endpoint() -> None:
    dep = rbac.require_role("admin")
    with pytest.raises(HTTPException) as exc:
        await dep(x_sentinel_role="viewer")
    assert exc.value.status_code == 403


async def test_admin_allowed() -> None:
    dep = rbac.require_role("admin")
    assert await dep(x_sentinel_role="admin") == "admin"


async def test_analyst_allowed_on_analyst_endpoint() -> None:
    dep = rbac.require_role("analyst")
    assert await dep(x_sentinel_role="analyst") == "analyst"


async def test_missing_role_denied() -> None:
    dep = rbac.require_role("analyst")
    with pytest.raises(HTTPException):
        await dep(x_sentinel_role=None)


async def test_disabled_rbac_allows_anyone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rbac_enabled", False)
    dep = rbac.require_role("admin")
    # No role header, RBAC off → treated as admin (dev mode), no exception.
    assert await dep(x_sentinel_role=None) == "admin"
