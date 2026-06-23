"""Connectors API: CRUD + runtime status. Secrets are redacted in responses."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.manager import PUSH_TYPES, REGISTRY
from app.core.metadata_db import get_db
from app.models.connector import (
    Connector,
    ConnectorCreate,
    ConnectorResponse,
    ConnectorUpdate,
    redact_config,
)

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

_KNOWN_TYPES = set(REGISTRY) | PUSH_TYPES


def _to_response(row: Connector) -> ConnectorResponse:
    resp = ConnectorResponse.model_validate(row)
    resp.config = redact_config(row.config)
    return resp


@router.get("", response_model=list[ConnectorResponse])
async def list_connectors(db: AsyncSession = Depends(get_db)) -> list[ConnectorResponse]:
    rows = (await db.execute(select(Connector))).scalars().all()
    return [_to_response(r) for r in rows]


@router.post("", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(
    payload: ConnectorCreate, db: AsyncSession = Depends(get_db)
) -> ConnectorResponse:
    if payload.type not in _KNOWN_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown connector type '{payload.type}'. Known: {sorted(_KNOWN_TYPES)}",
        )
    row = Connector(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_response(row)


@router.patch("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: int, payload: ConnectorUpdate, db: AsyncSession = Depends(get_db)
) -> ConnectorResponse:
    row = await db.get(Connector, connector_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="connector not found")
    data: dict[str, Any] = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return _to_response(row)


@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector(connector_id: int, db: AsyncSession = Depends(get_db)) -> None:
    row = await db.get(Connector, connector_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="connector not found")
    await db.delete(row)
    await db.commit()
