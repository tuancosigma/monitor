"""``GET /events`` — filtered, parameterized log query + ``/events/stream`` SSE tail.

Security: filter columns are whitelisted (never taken from client-supplied column
names) and all values bind as ClickHouse query parameters — no string interpolation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core import clickhouse
from app.ingest.clickhouse_writer import COLUMN_NAMES
from app.realtime.sse import event_stream, hub

router = APIRouter(tags=["events"])

# Whitelist: client filter name -> (ClickHouse column, match mode).
_FILTERS: dict[str, tuple[str, str]] = {
    "host_name": ("host_name", "eq"),
    "source_ip": ("source_ip", "eq"),
    "user_name": ("user_name", "eq"),
    "event_category": ("event_category", "eq"),
    "min_severity": ("event_severity", "gte"),
    "message": ("message", "like"),
}

_MAX_LIMIT = 1000


@router.get("/events")
async def list_events(
    start: datetime | None = None,
    end: datetime | None = None,
    host_name: Annotated[str | None, Query()] = None,
    source_ip: Annotated[str | None, Query()] = None,
    user_name: Annotated[str | None, Query()] = None,
    event_category: Annotated[str | None, Query()] = None,
    min_severity: Annotated[int | None, Query(ge=0, le=100)] = None,
    message: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    # Default to a bounded 24h window so unscoped queries stay fast.
    end_dt = end or datetime.now(UTC)
    start_dt = start or (end_dt - timedelta(hours=24))

    where = ["`@timestamp` BETWEEN %(start)s AND %(end)s"]
    params: dict[str, Any] = {"start": start_dt, "end": end_dt}

    supplied = {
        "host_name": host_name,
        "source_ip": source_ip,
        "user_name": user_name,
        "event_category": event_category,
        "min_severity": min_severity,
        "message": message,
    }
    for name, value in supplied.items():
        if value is None:
            continue
        column, mode = _FILTERS[name]
        key = f"f_{name}"
        if mode == "eq":
            where.append(f"{column} = %({key})s")
            params[key] = value
        elif mode == "gte":
            where.append(f"{column} >= %({key})s")
            params[key] = value
        elif mode == "like":
            where.append(f"positionCaseInsensitive({column}, %({key})s) > 0")
            params[key] = value

    params["limit"] = limit
    params["offset"] = offset
    # SQL is assembled only from server-side whitelists (COLUMN_NAMES + fixed WHERE
    # fragments from _FILTERS); every client value binds as a query parameter.
    columns = ", ".join(f"`{c}`" for c in COLUMN_NAMES)
    sql = (
        f"SELECT {columns} FROM events "  # noqa: S608 — whitelisted identifiers; values bound
        f"WHERE {' AND '.join(where)} "
        f"ORDER BY `@timestamp` DESC LIMIT %(limit)s OFFSET %(offset)s"
    )
    result = await clickhouse.execute(sql, params)
    rows = [dict(zip(COLUMN_NAMES, row, strict=True)) for row in result.result_rows]
    return {"count": len(rows), "events": rows}


@router.get("/events/stream")
async def stream_events() -> StreamingResponse:
    """Live tail via SSE. Each newly-ingested event is pushed as a JSON data frame."""
    queue = hub.subscribe()
    return StreamingResponse(
        event_stream(queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
