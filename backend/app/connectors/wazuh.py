"""Wazuh connector: poll the Wazuh alerts API and map to ECS-lite.

Outbound requests go through the SSRF-guarded client (the upstream URL is operator-
configured). The mapping function is pure and unit-tested independently of transport.
"""

from __future__ import annotations

from typing import Any

from app.connectors.base import ConnectorBase
from app.core.logging import get_logger
from app.core.ssrf_guard import get_safe_client

log = get_logger("sentinel.connectors.wazuh")


def map_wazuh_alert(alert: dict[str, Any]) -> dict[str, Any]:
    """Map one Wazuh alert object to an ECS-lite event dict (missing fields omitted)."""
    rule = alert.get("rule", {}) or {}
    agent = alert.get("agent", {}) or {}
    data = alert.get("data", {}) or {}
    mitre = rule.get("mitre", {}) or {}

    # Wazuh rule.level is 0..15 → scale to ECS 0..100.
    level = int(rule.get("level", 0) or 0)
    severity = min(100, level * 7)

    ecs: dict[str, Any] = {
        "@timestamp": alert.get("timestamp"),
        "event.kind": "alert",
        "event.category": "intrusion_detection",
        "event.action": rule.get("description") or "wazuh_alert",
        "event.severity": severity,
        "event.dataset": "wazuh.alerts",
        "message": rule.get("description"),
        "observer.vendor": "Wazuh",
        "observer.product": "Wazuh",
        "raw": None,  # filled by validate.parse_event from the JSON payload
    }
    if agent.get("name"):
        ecs["host.name"] = agent["name"]
    if agent.get("ip"):
        ecs["host.ip"] = [agent["ip"]]
    if data.get("srcip"):
        ecs["source.ip"] = data["srcip"]
    if data.get("srcuser") or data.get("dstuser"):
        ecs["user.name"] = data.get("srcuser") or data.get("dstuser")

    # MITRE mapping (Wazuh stores id/tactic/technique as arrays).
    ids = mitre.get("id") or []
    if ids:
        ecs["threat.technique.id"] = ids[0] if isinstance(ids, list) else ids
    tactics = mitre.get("tactic") or []
    if tactics:
        ecs["threat.tactic.name"] = tactics[0] if isinstance(tactics, list) else tactics
    techniques = mitre.get("technique") or []
    if techniques:
        ecs["threat.technique.name"] = (
            techniques[0] if isinstance(techniques, list) else techniques
        )
    return {k: v for k, v in ecs.items() if v is not None}


class WazuhConnector(ConnectorBase):
    type = "wazuh"

    async def _authenticate(self) -> str:
        base = str(self.config["base_url"]).rstrip("/")
        user = self.config.get("username", "")
        password = self.config.get("password", "")
        async with get_safe_client() as client:
            resp = await client.post(
                f"{base}/security/user/authenticate",
                auth=(user, password),
                timeout=10.0,
            )
            resp.raise_for_status()
            token: str = resp.json()["data"]["token"]
            return token

    async def fetch(self, cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
        base = str(self.config["base_url"]).rstrip("/")
        token = await self._authenticate()
        params: dict[str, Any] = {"sort": "timestamp", "limit": 500}
        if cursor:
            params["q"] = f"timestamp>{cursor}"

        async with get_safe_client() as client:
            resp = await client.get(
                f"{base}/alerts",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=15.0,
            )
            resp.raise_for_status()
            items = resp.json().get("data", {}).get("affected_items", [])

        events = [map_wazuh_alert(a) for a in items]
        new_cursor = items[-1].get("timestamp") if items else cursor
        log.info("wazuh_polled", count=len(events))
        return events, new_cursor
