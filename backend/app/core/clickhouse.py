"""Async ClickHouse access.

clickhouse-connect is synchronous; we wrap calls in ``asyncio.to_thread`` so the
event loop is never blocked. A single shared client is created lazily.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("sentinel.clickhouse")

_client: Client | None = None
_lock = asyncio.Lock()
_query_lock = asyncio.Lock()

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _connect() -> Client:
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


async def get_client() -> Client:
    """Return the shared client, connecting on first use."""
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                _client = await asyncio.to_thread(_connect)
    return _client


async def execute(query: str, parameters: dict[str, Any] | None = None) -> Any:
    client = await get_client()
    async with _query_lock:
        return await asyncio.to_thread(client.query, query, parameters or {})


async def insert_rows(table: str, rows: list[list[Any]], column_names: list[str]) -> None:
    client = await get_client()
    async with _query_lock:
        await asyncio.to_thread(client.insert, table, rows, column_names=column_names)


async def run_migrations() -> None:
    """Apply every ``*.sql`` file in migrations/ in lexical order (idempotent DDL)."""
    client = await get_client()
    async with _query_lock:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            if "-- target: sqlite" in sql:
                log.info("migration_skipped_sqlite", file=path.name)
                continue
            for statement in (s.strip() for s in sql.split(";")):
                if statement:
                    await asyncio.to_thread(client.command, statement)
            log.info("migration_applied", file=path.name)

