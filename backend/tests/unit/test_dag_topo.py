"""Unit tests for SOAR DAG validation + topological ordering."""

from __future__ import annotations

import pytest

from app.soar.dag import DagError, validate_dag


def _nodes(*ids: str) -> list[dict[str, object]]:
    return [{"id": i, "action": "tag", "params": {}} for i in ids]


def test_linear_chain_orders_correctly() -> None:
    order = validate_dag(_nodes("a", "b", "c"), [["a", "b"], ["b", "c"]])
    assert order == ["a", "b", "c"]


def test_independent_nodes_sorted_deterministically() -> None:
    order = validate_dag(_nodes("b", "a", "c"), [])
    assert order == ["a", "b", "c"]  # sorted for determinism


def test_diamond_respects_dependencies() -> None:
    edges = [["a", "b"], ["a", "c"], ["b", "d"], ["c", "d"]]
    order = validate_dag(_nodes("a", "b", "c", "d"), edges)
    assert order[0] == "a"
    assert order[-1] == "d"
    assert order.index("b") < order.index("d")


def test_cycle_rejected() -> None:
    with pytest.raises(DagError, match="cycle"):
        validate_dag(_nodes("a", "b"), [["a", "b"], ["b", "a"]])


def test_dangling_edge_rejected() -> None:
    with pytest.raises(DagError, match="unknown node"):
        validate_dag(_nodes("a"), [["a", "ghost"]])


def test_duplicate_id_rejected() -> None:
    with pytest.raises(DagError, match="duplicate"):
        validate_dag(_nodes("a", "a"), [])
