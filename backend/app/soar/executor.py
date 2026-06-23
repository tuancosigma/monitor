"""Playbook executor: topo-walk the DAG, run actions, gate dangerous ones, audit the run.

Context (triggering entity + prior node outputs) flows to each node. A dangerous action
is blocked unless the playbook is ``auto_approve`` or the caller passes ``confirm_dangerous``;
in dry-run every action is a no-op that reports what it *would* do. The run is persisted
as the audit record regardless of outcome.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.playbook import Playbook, PlaybookRun
from app.soar import audit
from app.soar.actions.base import ActionContext, get_action, is_dangerous
from app.soar.dag import DagError, validate_dag

log = get_logger("sentinel.soar.executor")


async def execute_playbook(
    db: AsyncSession,
    playbook: Playbook,
    trigger_type: str,
    trigger: dict[str, Any],
    *,
    dry_run: bool = False,
    confirm_dangerous: bool = False,
) -> PlaybookRun:
    nodes_by_id = {n["id"]: n for n in playbook.nodes}
    try:
        order = validate_dag(playbook.nodes, playbook.edges)
    except DagError as err:
        return await audit.record_run(
            db, playbook_id=playbook.id, dry_run=dry_run, trigger_context=trigger,
            node_results=[{"error": f"invalid dag: {err}"}], status="failed",
        )

    ctx = ActionContext(db=db, trigger_type=trigger_type, trigger=trigger, dry_run=dry_run)
    node_results: list[dict[str, Any]] = []
    status = "dry_run" if dry_run else "success"

    for node_id in order:
        node = nodes_by_id[node_id]
        action_name = node.get("action", "")
        params = node.get("params", {})
        action = get_action(action_name)

        if action is None:
            node_results.append(
                {"node_id": node_id, "action": action_name, "status": "error",
                 "output": "unknown action"}
            )
            status = "failed"
            break

        # Dangerous-action confirmation gate (dry-run bypasses since it is a no-op).
        if is_dangerous(action_name) and not dry_run and not (
            playbook.auto_approve or confirm_dangerous
        ):
            node_results.append(
                {"node_id": node_id, "action": action_name, "status": "blocked",
                 "output": "dangerous action requires confirmation or auto_approve"}
            )
            status = "blocked"
            break

        try:
            result = await action(params, ctx)
        except Exception as exc:
            node_results.append(
                {"node_id": node_id, "action": action_name, "status": "error",
                 "output": str(exc)}
            )
            status = "failed"
            log.warning("soar_node_failed", node=node_id, action=action_name, error=str(exc))
            break

        ctx.node_outputs[node_id] = result.output
        node_results.append(
            {"node_id": node_id, "action": action_name, "status": result.status,
             "output": result.output}
        )

    return await audit.record_run(
        db, playbook_id=playbook.id, dry_run=dry_run, trigger_context=trigger,
        node_results=node_results, status=status,
    )
