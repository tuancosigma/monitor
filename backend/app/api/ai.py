"""AI endpoints: alert triage, NL->SQL generation + approved execution, usage ledger."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.ledger import ledger
from app.ai.gateway.router import NoCapacity
from app.ai.gateway.structured import StructuredOutputError
from app.ai.nl2sql import question_to_sql
from app.ai.sql_guard import UnsafeSqlError
from app.ai.triage import triage_alert
from app.core.clickhouse_readonly import run_readonly_select
from app.core.metadata_db import get_db
from app.models.alert import Alert

router = APIRouter(prefix="/api/ai", tags=["ai"])


class NlQuery(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class SqlRun(BaseModel):
    sql: str = Field(min_length=1, max_length=10000)


@router.post("/triage/{alert_id}")
async def triage(alert_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    alert = (await db.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found")
    try:
        return await triage_alert(alert)
    except NoCapacity as err:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI busy, retry later: {err}"
        ) from err
    except StructuredOutputError as err:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail=f"AI returned invalid output: {err}"
        ) from err


@router.post("/nl2sql")
async def nl2sql(payload: NlQuery) -> dict[str, str]:
    """Generate a guarded SELECT from a question. SQL is returned for user approval, not run."""
    try:
        sql = await question_to_sql(payload.question)
    except UnsafeSqlError as err:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"Generated SQL rejected: {err}"
        ) from err
    except NoCapacity as err:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI busy, retry later: {err}"
        ) from err
    except StructuredOutputError as err:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail=f"AI returned invalid output: {err}"
        ) from err
    return {"sql": sql}


@router.post("/nl2sql/run")
async def nl2sql_run(payload: SqlRun) -> dict[str, Any]:
    """Execute a user-approved SELECT read-only. Re-guarded server-side."""
    try:
        return await run_readonly_select(payload.sql)
    except UnsafeSqlError as err:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"SQL rejected: {err}"
        ) from err


@router.get("/usage")
async def usage() -> dict[str, Any]:
    return {
        "usage": [
            {
                "provider": r.provider,
                "account": r.account,
                "task": r.task,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "calls": r.calls,
            }
            for r in ledger.rows()
        ]
    }
