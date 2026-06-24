"""Unit tests for dashboard widget aggregation (no live ClickHouse).

The ClickHouse round-trip is stubbed; these tests pin the contract:
field whitelisting, widget-type validation, response shaping, and the
heatmap zero-fill that the strip renderer depends on.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.dashboard import widget_query


class _FakeResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.result_rows = rows


def _stub_execute(rows: list[tuple[Any, ...]]):
    async def _execute(_sql: str, _params: dict[str, Any] | None = None) -> _FakeResult:
        return _FakeResult(rows)

    return _execute


async def test_unknown_widget_type_raises() -> None:
    with pytest.raises(ValueError, match="unknown widget type"):
        await widget_query.query_widget("piechart", "event_category", 60)


async def test_top_n_rejects_non_whitelisted_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(widget_query.clickhouse, "execute", _stub_execute([]))
    with pytest.raises(ValueError, match="unknown field"):
        await widget_query.query_widget("top_n", "; DROP TABLE events", 60)


async def test_top_n_shapes_series(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        widget_query.clickhouse,
        "execute",
        _stub_execute([("authentication", 12), ("network", 7)]),
    )
    out = await widget_query.query_widget("top_n", "event_category", 1440)
    assert out["type"] == "top_n"
    assert out["series"] == [
        {"label": "authentication", "value": 12},
        {"label": "network", "value": 7},
    ]


async def test_heatmap_zero_fills_24_hours(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        widget_query.clickhouse, "execute", _stub_execute([(0, 5), (13, 40)])
    )
    out = await widget_query.query_widget("heatmap", "event_category", 1440)
    series = out["series"]
    assert len(series) == 24
    assert series[0] == {"label": "00", "value": 5}
    assert series[13] == {"label": "13", "value": 40}
    assert series[1] == {"label": "01", "value": 0}  # zero-filled


async def test_log_table_returns_events(monkeypatch: pytest.MonkeyPatch) -> None:
    row = ("2026-06-24T00:00:00+00:00", "auth", 80, "host1", "10.0.0.1", "root", "failed login")
    monkeypatch.setattr(widget_query.clickhouse, "execute", _stub_execute([row]))
    out = await widget_query.query_widget("log_table", "event_category", 60)
    assert "events" in out
    assert out["events"][0]["host_name"] == "host1"
    assert out["events"][0]["message"] == "failed login"
