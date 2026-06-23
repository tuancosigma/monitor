"""DAG validation + topological ordering for playbooks.

Nodes are [{id, action, params}]; edges are [[from_id, to_id]]. The executor runs nodes
in topological order. Cycles, dangling edges, duplicate ids, and over-large graphs are
rejected up front so a playbook can never loop forever or reference missing nodes.
"""

from __future__ import annotations

from collections import deque
from typing import Any

MAX_NODES = 100


class DagError(Exception):
    """The playbook graph is invalid (cycle, dangling edge, duplicate id, too large)."""


def validate_dag(nodes: list[dict[str, Any]], edges: list[list[str]]) -> list[str]:
    """Validate the graph and return node ids in topological order.

    Raises DagError on any structural problem.
    """
    if len(nodes) > MAX_NODES:
        raise DagError(f"too many nodes (>{MAX_NODES})")

    ids = [n["id"] for n in nodes]
    if len(ids) != len(set(ids)):
        raise DagError("duplicate node id")
    id_set = set(ids)

    adjacency: dict[str, list[str]] = {nid: [] for nid in ids}
    indegree: dict[str, int] = {nid: 0 for nid in ids}
    for edge in edges:
        if len(edge) != 2:
            raise DagError(f"edge must have exactly 2 endpoints: {edge}")
        src, dst = edge
        if src not in id_set or dst not in id_set:
            raise DagError(f"edge references unknown node: {edge}")
        adjacency[src].append(dst)
        indegree[dst] += 1

    # Kahn's algorithm — emits a topo order or detects a cycle.
    queue: deque[str] = deque(sorted(nid for nid in ids if indegree[nid] == 0))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in sorted(adjacency[node]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(ids):
        raise DagError("graph contains a cycle")
    return order
