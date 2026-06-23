"""API endpoints for managing security Incidents."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.metadata_db import get_db
from app.models.incident import (
    Incident,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentUpdate,
)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    status: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
) -> list[Incident]:
    """Retrieve incidents, optionally filtered by status or severity."""
    stmt = select(Incident)

    if status:
        stmt = stmt.where(Incident.status == status.lower())
    if severity:
        stmt = stmt.where(Incident.severity == severity.lower())

    stmt = stmt.order_by(Incident.last_seen.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> Incident:
    """Retrieve a single incident by ID, including its associated alerts."""
    stmt = (
        select(Incident)
        .options(selectinload(Incident.alerts))
        .where(Incident.id == incident_id)
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found",
        )

    # Sort alerts in chronological order for the timeline rendering
    incident.alerts.sort(key=lambda a: a.timestamp)
    return incident


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: int,
    incident_in: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
) -> Incident:
    """Update incident metadata (assignee, status, description, severity, or title)."""
    stmt = select(Incident).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found",
        )

    # Update valid fields
    update_data = incident_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)

    await db.commit()
    await db.refresh(incident)
    return incident
