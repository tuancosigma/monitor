"""Built-in SOAR actions. Each reuses an existing subsystem rather than re-implementing it.

- notify       -> P3 notification router (route the triggering alert/incident)
- ai_triage    -> P4 gateway triage; attaches the summary to the incident
- http         -> P5 ssrf_guard + resilience (dangerous: external call)
- script       -> constrained subprocess sandbox (dangerous: RCE surface)
- tag          -> append a tag entity to the triggering alert/incident
- close_incident -> set incident status=closed (dangerous: destructive)
"""

from __future__ import annotations

from typing import Any

from app.ai.triage import triage_alert
from app.alerting.router import route_alert, route_incident
from app.core.resilience import retry_async
from app.core.script_sandbox import run_script
from app.core.ssrf_guard import get_safe_client
from app.models.alert import Alert
from app.models.incident import Incident
from app.soar.actions.base import ActionContext, ActionResult, register


def _trigger_id(ctx: ActionContext) -> int | None:
    raw = ctx.trigger.get("id")
    return int(raw) if raw is not None else None


@register("notify")
async def notify(params: dict[str, Any], ctx: ActionContext) -> ActionResult:
    if ctx.dry_run:
        return ActionResult("planned", {"would_notify": ctx.trigger_type})
    entity_id = _trigger_id(ctx)
    if entity_id is None:
        return ActionResult("skipped", "no triggering entity to notify on")
    if ctx.trigger_type == "incident":
        await route_incident(ctx.db, entity_id)
    else:
        await route_alert(ctx.db, entity_id)
    return ActionResult("ok", {"notified": ctx.trigger_type, "id": entity_id})


@register("ai_triage")
async def ai_triage(params: dict[str, Any], ctx: ActionContext) -> ActionResult:
    if ctx.dry_run:
        return ActionResult("planned", {"would_triage_alert": _trigger_id(ctx)})
    alert_id = _trigger_id(ctx)
    if alert_id is None:
        return ActionResult("skipped", "ai_triage needs an alert trigger")
    alert = await ctx.db.get(Alert, alert_id)
    if alert is None:
        return ActionResult("error", f"alert {alert_id} not found")
    result = await triage_alert(alert)
    # Attach the summary to the correlated incident, if any.
    if alert.incident_id is not None:
        incident = await ctx.db.get(Incident, alert.incident_id)
        if incident is not None:
            incident.description = f"[AI] {result['summary']}\n{incident.description}"[:1000]
            await ctx.db.commit()
    return ActionResult("ok", result)


@register("tag")
async def tag(params: dict[str, Any], ctx: ActionContext) -> ActionResult:
    tags = params.get("tags", [])
    if ctx.dry_run:
        return ActionResult("planned", {"would_tag": tags})
    entity_id = _trigger_id(ctx)
    if entity_id is None:
        return ActionResult("skipped", "no triggering entity to tag")
    entity: Alert | Incident | None = (
        await ctx.db.get(Incident, entity_id)
        if ctx.trigger_type == "incident"
        else await ctx.db.get(Alert, entity_id)
    )
    if entity is None:
        return ActionResult("error", "entity not found")
    entities = list(entity.entities or [])
    entities.extend({"type": "tag", "value": str(t)} for t in tags)
    entity.entities = entities
    await ctx.db.commit()
    return ActionResult("ok", {"tagged": tags})


@register("close_incident", dangerous=True)
async def close_incident(params: dict[str, Any], ctx: ActionContext) -> ActionResult:
    if ctx.dry_run:
        return ActionResult("planned", {"would_close_incident": _trigger_id(ctx)})
    entity_id = _trigger_id(ctx)
    if ctx.trigger_type != "incident" or entity_id is None:
        return ActionResult("skipped", "close_incident needs an incident trigger")
    incident = await ctx.db.get(Incident, entity_id)
    if incident is None:
        return ActionResult("error", "incident not found")
    incident.status = "closed"
    await ctx.db.commit()
    return ActionResult("ok", {"closed_incident": entity_id})


@register("http", dangerous=True)
async def http(params: dict[str, Any], ctx: ActionContext) -> ActionResult:
    url = params.get("url")
    method = str(params.get("method", "POST")).upper()
    body = params.get("body")
    if not url:
        return ActionResult("error", "http action requires 'url'")
    if ctx.dry_run:
        return ActionResult("planned", {"would_call": f"{method} {url}"})

    async def _call() -> int:
        async with get_safe_client() as client:  # SSRF-guarded
            resp = await client.request(method, url, json=body, timeout=10.0)
            resp.raise_for_status()
            return resp.status_code

    status_code = await retry_async(_call, attempts=3)
    return ActionResult("ok", {"status_code": status_code})


@register("script", dangerous=True)
async def script(params: dict[str, Any], ctx: ActionContext) -> ActionResult:
    command = params.get("command", [])
    if ctx.dry_run:
        return ActionResult("planned", {"would_run": command})
    result = await run_script(list(command))
    return ActionResult("ok", result)
