"""Audit API: query the append-only audit log (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metadata_db import get_db
from app.core.rbac import require_role
from app.models.audit_log import AuditLog, AuditLogResponse

router = APIRouter(
    prefix="/api/audit", tags=["audit"], dependencies=[Depends(require_role("admin"))]
)


@router.get("", response_model=list[AuditLogResponse])
async def list_audit(
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLog]:
    return list(
        (await db.execute(select(AuditLog).order_by(desc(AuditLog.ts)).limit(limit)))
        .scalars()
        .all()
    )
