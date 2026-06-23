"""Dashboard API: load + save a per-owner widget layout (JSON)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metadata_db import get_db
from app.models.dashboard_layout import (
    DashboardLayout,
    DashboardLayoutPayload,
    DashboardLayoutResponse,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardLayoutResponse)
async def get_layout(owner: str = "default", db: AsyncSession = Depends(get_db)) -> DashboardLayout:
    row = (
        await db.execute(select(DashboardLayout).where(DashboardLayout.owner == owner))
    ).scalar_one_or_none()
    if row is None:
        return DashboardLayout(owner=owner, widgets=[])
    return row


@router.put("", response_model=DashboardLayoutResponse)
async def save_layout(
    payload: DashboardLayoutPayload, db: AsyncSession = Depends(get_db)
) -> DashboardLayout:
    row = (
        await db.execute(select(DashboardLayout).where(DashboardLayout.owner == payload.owner))
    ).scalar_one_or_none()
    if row is None:
        row = DashboardLayout(owner=payload.owner, widgets=payload.widgets)
        db.add(row)
    else:
        row.widgets = payload.widgets
    await db.commit()
    await db.refresh(row)
    return row
