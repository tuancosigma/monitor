"""Aggregate ClickHouse event data for dashboard widgets.

Security: the grouping/aggregation field is whitelisted against the ingested
column set (``COLUMN_NAMES``); it is never taken verbatim from client input.
Time-window and limit are validated integers controlled server-side. Every
client-derived value binds as a ClickHouse query parameter — no string interp.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core import clickhouse
from app.ingest.clickhouse_writer import COLUMN_NAMES

WIDGET_TYPES = frozenset({"timeseries", "top_n", "heatmap", "log_table"})

# Fields a widget may group/aggregate on — exactly the ingested event columns.
_ALLOWED_FIELDS = frozenset(COLUMN_NAMES)

# Columns surfaced by a ``log_table`` widget (most useful triage subset).
_LOG_COLUMNS = (
    "@timestamp",
    "event_category",
    "event_severity",
    "host_name",
    "source_ip",
    "user_name",
    "message",
)

_MIN_MINUTES = 5
_MAX_MINUTES = 7 * 24 * 60  # 7 days
_TOP_N = 10
_LOG_LIMIT = 50
# Aim for ~30 buckets across the window so timeseries stays readable.
_TARGET_BUCKETS = 30


def _validate_field(field: str) -> str:
    if field not in _ALLOWED_FIELDS:
        raise ValueError(f"unknown field: {field!r}")
    return field


def _window_start(minutes: int) -> datetime:
    minutes = max(_MIN_MINUTES, min(_MAX_MINUTES, minutes))
    return datetime.now(UTC) - timedelta(minutes=minutes)


def _series(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [{"label": str(label), "value": int(value)} for label, value in rows]


async def _timeseries(minutes: int) -> list[dict[str, Any]]:
    bucket = max(1, minutes // _TARGET_BUCKETS)  # server-controlled int literal
    sql = (
        f"SELECT toStartOfInterval(`@timestamp`, INTERVAL {bucket} minute) AS b, "  # noqa: S608
        "count() AS c FROM events WHERE `@timestamp` >= %(start)s "
        "GROUP BY b ORDER BY b"
    )
    result = await clickhouse.execute(sql, {"start": _window_start(minutes)})
    return [
        {"label": b.isoformat() if hasattr(b, "isoformat") else str(b), "value": int(c)}
        for b, c in result.result_rows
    ]


async def _top_n(field: str, minutes: int) -> list[dict[str, Any]]:
    col = _validate_field(field)
    sql = (
        f"SELECT `{col}` AS k, count() AS c FROM events "  # noqa: S608 — col whitelisted
        "WHERE `@timestamp` >= %(start)s AND `" + col + "` != '' "
        "GROUP BY k ORDER BY c DESC LIMIT %(limit)s"
    )
    result = await clickhouse.execute(
        sql, {"start": _window_start(minutes), "limit": _TOP_N}
    )
    return _series(result.result_rows)


async def _heatmap(minutes: int) -> list[dict[str, Any]]:
    """Event volume by hour-of-day (0-23), zero-filled for empty hours."""
    sql = (
        "SELECT toHour(`@timestamp`) AS h, count() AS c FROM events "  # noqa: S608
        "WHERE `@timestamp` >= %(start)s GROUP BY h"
    )
    result = await clickhouse.execute(sql, {"start": _window_start(minutes)})
    counts = {int(h): int(c) for h, c in result.result_rows}
    return [{"label": f"{h:02d}", "value": counts.get(h, 0)} for h in range(24)]


async def _log_table(minutes: int) -> list[dict[str, Any]]:
    cols = ", ".join(f"`{c}`" for c in _LOG_COLUMNS)
    sql = (
        f"SELECT {cols} FROM events WHERE `@timestamp` >= %(start)s "  # noqa: S608
        "ORDER BY `@timestamp` DESC LIMIT %(limit)s"
    )
    result = await clickhouse.execute(
        sql, {"start": _window_start(minutes), "limit": _LOG_LIMIT}
    )
    return [
        {
            col: (val.isoformat() if hasattr(val, "isoformat") else val)
            for col, val in zip(_LOG_COLUMNS, row, strict=True)
        }
        for row in result.result_rows
    ]


async def query_widget(widget_type: str, field: str, minutes: int) -> dict[str, Any]:
    """Return ``{type, field, series|events}`` for one dashboard widget."""
    if widget_type not in WIDGET_TYPES:
        raise ValueError(f"unknown widget type: {widget_type!r}")

    if widget_type == "timeseries":
        return {"type": widget_type, "field": field, "series": await _timeseries(minutes)}
    if widget_type == "top_n":
        return {"type": widget_type, "field": field, "series": await _top_n(field, minutes)}
    if widget_type == "heatmap":
        return {"type": widget_type, "field": field, "series": await _heatmap(minutes)}
    # log_table
    return {"type": widget_type, "field": field, "events": await _log_table(minutes)}
