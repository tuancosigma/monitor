"""Webhook-IN endpoint: POST /ingest/webhook/{source}.

Accepts external JSON, authenticates against the named webhook connector's per-source
token, maps the payload to ECS-lite, and emits it onto the shared ingest path.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import resolve_secrets
from app.connectors.webhook_in import map_webhook_payload
from app.core.metadata_db import get_db
from app.ingest.producer import producer
from app.models.connector import Connector

router = APIRouter(prefix="/ingest", tags=["ingest"])

_MAX_BODY_BYTES = 1_048_576  # 1 MiB payload cap


@router.post("/webhook/{source}", status_code=status.HTTP_202_ACCEPTED)
async def webhook_in(
    source: str,
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    body = await request.body()
    if len(body) > _MAX_BODY_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="payload too large")

    row = (
        await db.execute(
            select(Connector).where(Connector.name == source, Connector.type == "webhook")
        )
    ).scalar_one_or_none()
    if row is None or not row.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="webhook source not found")

    config = resolve_secrets(dict(row.config))
    expected = config.get("token")
    presented = authorization.removeprefix("Bearer ").strip() if authorization else None
    if not expected or presented != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid webhook token")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="payload must be a JSON object")

    mapping = config.get("mapping", {}) or {}
    event = map_webhook_payload(payload, mapping)
    await producer.publish(event)
    return {"accepted": True, "source": source}
