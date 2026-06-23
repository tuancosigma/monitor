"""Incident correlation engine.

Correlates incoming alerts into high-level Incidents based on shared entities (IP,
hostname, username) and a sliding time-window (default 5 minutes).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.alert import Alert
from app.models.incident import Incident

log = get_logger("sentinel.correlation")

CORRELATION_WINDOW_MINUTES = 5

SEVERITY_ORDER = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def extract_entities_from_alert(alert: Alert) -> list[dict[str, Any]]:
    """Extract entities (IP, username, hostname) from an alert's matched details.

    Ensures they are structured as unique dictionaries with 'type' and 'value'.
    """
    entities = []
    seen = set()

    # 1. Start with any entities already attached to the alert
    for ent in alert.entities:
        t, v = ent.get("type"), ent.get("value")
        if t and v:
            key = (t, v)
            if key not in seen:
                seen.add(key)
                entities.append({"type": t, "value": v})

    # 2. Extract from sample events if entities list is empty
    for sample in alert.sample_events:
        # Check source IP
        src_ip = sample.get("source_ip")
        if src_ip and (isinstance(src_ip, str) and src_ip.strip() and src_ip != "0.0.0.0"):  # noqa: S104
            key = ("ip", src_ip)
            if key not in seen:
                seen.add(key)
                entities.append({"type": "ip", "value": src_ip})

        # Check destination IP
        dest_ip = sample.get("destination_ip")
        if dest_ip and (isinstance(dest_ip, str) and dest_ip.strip() and dest_ip != "0.0.0.0"):  # noqa: S104
            key = ("ip", dest_ip)
            if key not in seen:
                seen.add(key)
                entities.append({"type": "ip", "value": dest_ip})

        # Check username
        username = sample.get("user_name")
        if username and (isinstance(username, str) and username.strip()):
            key = ("username", username)
            if key not in seen:
                seen.add(key)
                entities.append({"type": "username", "value": username})

        # Check host name
        hostname = sample.get("host_name")
        if hostname and (isinstance(hostname, str) and hostname.strip()):
            key = ("hostname", hostname)
            if key not in seen:
                seen.add(key)
                entities.append({"type": "hostname", "value": hostname})

    return entities


def _make_naive(dt: datetime) -> datetime:
    """Ensure datetime is offset-naive UTC."""
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


async def correlate_alert(db: AsyncSession, alert: Alert) -> tuple[Incident, bool]:
    """Correlate a new Alert into an existing Incident or create a new one."""
    # Ensure alert has extracted entities populated
    entities = extract_entities_from_alert(alert)
    alert.entities = entities

    # Normalize alert timestamp to naive UTC
    alert_ts = _make_naive(alert.timestamp)
    alert.timestamp = alert_ts

    # Define sliding window boundary
    window_start = alert_ts - timedelta(minutes=CORRELATION_WINDOW_MINUTES)
    window_end = alert_ts + timedelta(minutes=CORRELATION_WINDOW_MINUTES)

    # Query all open/investigating incidents in the timeframe window
    result = await db.execute(
        select(Incident)
        .where(
            Incident.status.in_(["open", "investigating"]),
            Incident.last_seen >= window_start,
            Incident.first_seen <= window_end,
        )
    )
    incidents = result.scalars().all()

    matching_incident: Incident | None = None

    # Check for a shared entity
    for inc in incidents:
        shared_entity = False
        for inc_ent in inc.entities:
            for al_ent in entities:
                if (
                    inc_ent.get("type") == al_ent.get("type")
                    and inc_ent.get("value") == al_ent.get("value")
                ):
                    shared_entity = True
                    break
            if shared_entity:
                break

        if shared_entity:
            matching_incident = inc
            break

    if matching_incident:
        # Merge alert into existing incident
        log.info(
            "alert_merged_into_incident",
            alert_id=alert.id,
            incident_id=matching_incident.id,
        )
        alert.incident_id = matching_incident.id
        is_new = False


        # Normalize incident times to naive UTC before comparison
        inc_first = _make_naive(matching_incident.first_seen)
        inc_last = _make_naive(matching_incident.last_seen)

        # Update timestamps
        if alert_ts < inc_first:
            matching_incident.first_seen = alert_ts
        else:
            matching_incident.first_seen = inc_first

        if alert_ts > inc_last:
            matching_incident.last_seen = alert_ts
        else:
            matching_incident.last_seen = inc_last

        # Merge entity list
        existing_entities = {
            (e.get("type"), e.get("value"))
            for e in matching_incident.entities
            if e.get("type") and e.get("value")
        }
        for al_ent in entities:
            key = (al_ent.get("type"), al_ent.get("value"))
            if key not in existing_entities:
                matching_incident.entities.append(al_ent)

        # Upgrade incident severity if alert is higher
        al_sev = SEVERITY_ORDER.get(alert.severity.lower(), 0)
        inc_sev = SEVERITY_ORDER.get(matching_incident.severity.lower(), 0)
        if al_sev > inc_sev:
            matching_incident.severity = alert.severity

        # Update description to mention adding rule
        if alert.rule_name not in matching_incident.description:
            matching_incident.description += f", {alert.rule_name}"

    else:
        # Create a new Incident
        primary_entity_str = "unknown entity"
        if entities:
            # Pick username first, then IP, then host
            by_type = {e.get("type"): e.get("value") for e in entities}
            if "username" in by_type:
                primary_entity_str = f"user '{by_type['username']}'"
            elif "ip" in by_type:
                primary_entity_str = f"IP {by_type['ip']}"
            elif "hostname" in by_type:
                primary_entity_str = f"host {by_type['hostname']}"

        title = f"Security Incident: Suspected activity on {primary_entity_str}"
        description = f"Correlated incident triggered by detection: {alert.rule_name}"

        matching_incident = Incident(
            title=title,
            description=description,
            severity=alert.severity,
            status="open",
            first_seen=alert_ts,
            last_seen=alert_ts,
            entities=entities,
        )
        db.add(matching_incident)
        # Flush to generate matching_incident.id
        await db.flush()

        log.info(
            "new_incident_created",
            incident_id=matching_incident.id,
            trigger_alert_id=alert.id,
        )
        alert.incident_id = matching_incident.id
        is_new = True

    return matching_incident, is_new

