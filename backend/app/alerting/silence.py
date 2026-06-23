"""Silence check utility for muting notifications."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.incident import Incident
from app.models.silence import Silence


async def is_silenced(db: AsyncSession, target: Alert | Incident) -> bool:
    """Check if an Alert or Incident matches any active Silence rules.

    Returns True if target is silenced, False otherwise.
    """
    now = datetime.now(UTC)
    
    # SQLite naive datetimes check: if silence times are timezone-naive,
    # make them tz-aware or naive to compare.
    # We query silences active at 'now'.
    stmt = select(Silence).where(Silence.is_active)
    res = await db.execute(stmt)
    silences = res.scalars().all()

    for silence in silences:
        # Normalize DB datetimes to tz-aware UTC for comparison
        start = silence.start_time
        end = silence.end_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
            
        if not (start <= now <= end):
            continue

        filters = silence.filters
        if not filters:
            continue

        matches_all = True

        # 1. Severity filter check
        if "severity" in filters:
            sev_filter = filters["severity"]
            if isinstance(sev_filter, str):
                if target.severity.lower() != sev_filter.lower():
                    matches_all = False
            elif isinstance(sev_filter, list):
                if target.severity.lower() not in [s.lower() for s in sev_filter]:
                    matches_all = False

        # 2. Rule ID filter check
        if "rule_id" in filters and matches_all:
            rule_filter = filters["rule_id"]
            if isinstance(target, Alert):
                if target.rule_id != rule_filter:
                    matches_all = False
            elif isinstance(target, Incident):
                # Eager-load alerts if needed, check if any alert rule matches
                # If we don't have loaded alerts, we can try to inspect incident.alerts.
                # To be safe, we can do a quick check.
                try:
                    alert_rules = {a.rule_id for a in target.alerts}
                    if rule_filter not in alert_rules:
                        matches_all = False
                except Exception:
                    # If relation is not loaded and session is detached,
                    # fallback to string check in description
                    if rule_filter not in target.description:
                        matches_all = False

        # 3. Entity value filter check
        if "entity_value" in filters and matches_all:
            ent_filter = filters["entity_value"]
            target_entities = {e.get("value") for e in target.entities if e.get("value")}
            if ent_filter not in target_entities:
                matches_all = False

        # If all specified filters matched, this silence muting rule is triggered!
        if matches_all:
            return True

    return False
