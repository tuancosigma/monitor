"""Playbooks API: CRUD + manual run + dry-run. DAG is validated on create/update."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metadata_db import get_db
from app.models.playbook import (
    Playbook,
    PlaybookCreate,
    PlaybookResponse,
    PlaybookRunResponse,
    PlaybookUpdate,
)
from app.soar.actions.base import get_action, known_actions
from app.soar.dag import DagError, validate_dag
from app.soar.executor import execute_playbook

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


class RunRequest(BaseModel):
    trigger: dict[str, Any] = Field(default_factory=dict)
    confirm_dangerous: bool = False


def _validate_definition(nodes: list[dict[str, Any]], edges: list[list[str]]) -> None:
    try:
        validate_dag(nodes, edges)
    except DagError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"invalid DAG: {err}") from err
    for node in nodes:
        if get_action(node.get("action", "")) is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"unknown action '{node.get('action')}'. Known: {known_actions()}",
            )


@router.get("", response_model=list[PlaybookResponse])
async def list_playbooks(db: AsyncSession = Depends(get_db)) -> list[Playbook]:
    return list((await db.execute(select(Playbook))).scalars().all())


@router.post("", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    payload: PlaybookCreate, db: AsyncSession = Depends(get_db)
) -> Playbook:
    nodes = [n.model_dump() for n in payload.nodes]
    _validate_definition(nodes, payload.edges)
    row = Playbook(**{**payload.model_dump(), "nodes": nodes})
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: int, payload: PlaybookUpdate, db: AsyncSession = Depends(get_db)
) -> Playbook:
    row = await db.get(Playbook, playbook_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="playbook not found")
    data = payload.model_dump(exclude_unset=True)
    if "nodes" in data:
        data["nodes"] = [n if isinstance(n, dict) else n.model_dump() for n in data["nodes"]]
    nodes = data.get("nodes", row.nodes)
    edges = data.get("edges", row.edges)
    _validate_definition(nodes, edges)
    for field, value in data.items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(playbook_id: int, db: AsyncSession = Depends(get_db)) -> None:
    row = await db.get(Playbook, playbook_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="playbook not found")
    await db.delete(row)
    await db.commit()


@router.post("/{playbook_id}/run", response_model=PlaybookRunResponse)
async def run_playbook(
    playbook_id: int, payload: RunRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    row = await db.get(Playbook, playbook_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="playbook not found")
    return await execute_playbook(
        db, row, row.trigger_type, payload.trigger,
        dry_run=False, confirm_dangerous=payload.confirm_dangerous,
    )


@router.post("/{playbook_id}/dry-run", response_model=PlaybookRunResponse)
async def dry_run_playbook(
    playbook_id: int, payload: RunRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    row = await db.get(Playbook, playbook_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="playbook not found")
    return await execute_playbook(db, row, row.trigger_type, payload.trigger, dry_run=True)
