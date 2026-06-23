"""Executor tests: ordered execution, dry-run no-op, dangerous-action gate, audit."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.metadata_db import Base
from app.models.playbook import Playbook
from app.soar.actions.base import ActionContext, ActionResult, register
from app.soar.executor import execute_playbook

_calls: list[str] = []


@register("test_track")
async def _track(params: dict[str, object], ctx: ActionContext) -> ActionResult:
    label = str(params.get("label"))
    _calls.append(label)
    return ActionResult("ok", label)


@register("test_danger", dangerous=True)
async def _danger(params: dict[str, object], ctx: ActionContext) -> ActionResult:
    if ctx.dry_run:  # real actions no-op in dry-run, reporting what they would do
        return ActionResult("planned", "would run")
    _calls.append("danger")
    return ActionResult("ok", "ran")


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture(autouse=True)
def _clear() -> None:
    _calls.clear()


async def _make_playbook(session: AsyncSession, **kwargs: object) -> Playbook:
    pb = Playbook(name=str(kwargs.get("name", "pb")), trigger_type="alert",
                  trigger_filter={}, **{k: v for k, v in kwargs.items() if k != "name"})
    session.add(pb)
    await session.commit()
    await session.refresh(pb)
    return pb


async def test_executes_in_topological_order(session: AsyncSession) -> None:
    pb = await _make_playbook(
        session,
        nodes=[
            {"id": "a", "action": "test_track", "params": {"label": "A"}},
            {"id": "b", "action": "test_track", "params": {"label": "B"}},
        ],
        edges=[["a", "b"]],
    )
    run = await execute_playbook(session, pb, "alert", {"type": "alert", "id": 1})
    assert run.status == "success"
    assert _calls == ["A", "B"]
    assert run.node_count == 2


async def test_dry_run_has_no_side_effects(session: AsyncSession) -> None:
    pb = await _make_playbook(
        session,
        nodes=[{"id": "a", "action": "test_danger", "params": {}}],
        edges=[],
    )
    run = await execute_playbook(session, pb, "alert", {"type": "alert", "id": 1}, dry_run=True)
    assert run.status == "dry_run"
    assert _calls == []  # action body never ran
    assert run.node_results[0]["status"] == "planned"


async def test_dangerous_blocked_without_confirmation(session: AsyncSession) -> None:
    pb = await _make_playbook(
        session,
        nodes=[{"id": "a", "action": "test_danger", "params": {}}],
        edges=[],
        auto_approve=False,
    )
    run = await execute_playbook(session, pb, "alert", {"type": "alert", "id": 1})
    assert run.status == "blocked"
    assert _calls == []


async def test_dangerous_runs_with_auto_approve(session: AsyncSession) -> None:
    pb = await _make_playbook(
        session,
        nodes=[{"id": "a", "action": "test_danger", "params": {}}],
        edges=[],
        auto_approve=True,
    )
    run = await execute_playbook(session, pb, "alert", {"type": "alert", "id": 1})
    assert run.status == "success"
    assert _calls == ["danger"]
