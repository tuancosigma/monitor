"""Unit tests for the NL->SQL safety guard."""

from __future__ import annotations

import pytest

from app.ai.sql_guard import DEFAULT_LIMIT, UnsafeSqlError, guard_select


def test_select_passes_and_gets_limit() -> None:
    out = guard_select("SELECT host_name FROM events WHERE event_severity > 50")
    assert "SELECT" in out.upper()
    assert "LIMIT" in out.upper()
    assert str(DEFAULT_LIMIT) in out


def test_existing_limit_preserved() -> None:
    out = guard_select("SELECT * FROM events LIMIT 5")
    assert "LIMIT 5" in out.upper().replace("  ", " ")


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO events VALUES (1)",
        "UPDATE events SET host_name='x'",
        "DELETE FROM events",
        "DROP TABLE events",
        "ALTER TABLE events ADD COLUMN x Int8",
        "CREATE TABLE t (a Int8)",
        "TRUNCATE TABLE events",
    ],
)
def test_non_select_rejected(sql: str) -> None:
    with pytest.raises(UnsafeSqlError):
        guard_select(sql)


def test_multi_statement_rejected() -> None:
    with pytest.raises(UnsafeSqlError):
        guard_select("SELECT 1; DROP TABLE events")


def test_system_command_rejected() -> None:
    with pytest.raises(UnsafeSqlError):
        guard_select("SYSTEM RELOAD CONFIG")


def test_empty_rejected() -> None:
    with pytest.raises(UnsafeSqlError):
        guard_select("   ")
