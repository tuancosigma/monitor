"""Execute user-approved, AI-generated SELECTs under a read-only ClickHouse session.

Defense-in-depth: the SQL is re-validated through sql_guard here (not trusted from the
caller), and the query runs with the ClickHouse ``readonly=1`` setting so even a guard
bypass cannot mutate data.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.ai.sql_guard import guard_select
from app.core import clickhouse


async def run_readonly_select(sql: str, max_rows: int = 1000) -> dict[str, Any]:
    """Re-guard and execute a SELECT read-only. Returns columns + rows."""
    safe_sql = guard_select(sql, limit=max_rows)
    client = await clickhouse.get_client()

    def _query() -> Any:
        # readonly=1 forbids writes/DDL at the server level regardless of SQL content.
        return client.query(safe_sql, settings={"readonly": 1, "max_result_rows": max_rows})

    result = await asyncio.to_thread(_query)
    return {
        "sql": safe_sql,
        "columns": list(result.column_names),
        "rows": [list(row) for row in result.result_rows],
    }
