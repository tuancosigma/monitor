"""API endpoints for managing security Alerts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metadata_db import get_db
from app.models.alert import Alert, AlertResponse, AlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    status: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
    rule_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
) -> list[Alert]:
    """Retrieve security alerts, optionally filtered by status, severity, or rule_id."""
    stmt = select(Alert)

    # Filter clauses
    if status:
        stmt = stmt.where(Alert.status == status.lower())
    if severity:
        stmt = stmt.where(Alert.severity == severity.lower())
    if rule_id:
        stmt = stmt.where(Alert.rule_id == rule_id)

    # Order by timestamp descending, apply offset and limit
    stmt = stmt.order_by(Alert.timestamp.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_in: AlertUpdate,
    db: AsyncSession = Depends(get_db),
) -> Alert:
    """Update alert metadata (assignee, status, or incident correlation)."""
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found",
        )

    # Update valid fields
    update_data = alert_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)
    return alert
