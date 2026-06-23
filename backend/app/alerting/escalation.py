"""Background escalation worker.

Periodically evaluates open, unacknowledged critical alerts or incidents
exceeding escalation thresholds, routing them to configured escalation channels.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.alerting.router import matches_criteria, route_alert, route_incident
from app.core.logging import get_logger
from app.core.metadata_db import AsyncSessionLocal
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.notification_log import NotificationLog
from app.models.routing_rule import RoutingRule

log = get_logger("sentinel.alerting.escalation")

_escalation_task: asyncio.Task[None] | None = None
_running = False


async def check_escalations() -> None:
    """Scan SQLite for unacknowledged alerts/incidents exceeding routing rule delays."""
    async with AsyncSessionLocal() as session:
        # Fetch active routing rules that have escalation configured
        stmt = select(RoutingRule).where(
            RoutingRule.is_active.is_(True),
            RoutingRule.escalation_delay_min.isnot(None),
        )
        res = await session.execute(stmt)
        rules = res.scalars().all()

        now = datetime.now(UTC)

        for rule in rules:
            delay = rule.escalation_delay_min
            if delay is None:
                continue
                
            cutoff = now - timedelta(minutes=delay)
            # Normalize to naive UTC for SQLite comparison
            cutoff_naive = cutoff.replace(tzinfo=None)

            # 1. Evaluate open Alerts
            alerts_stmt = select(Alert).where(
                Alert.status == "open",
                Alert.timestamp <= cutoff_naive,
            )
            alerts_res = await session.execute(alerts_stmt)
            alerts = alerts_res.scalars().all()

            for alert in alerts:
                if not matches_criteria(rule, alert):
                    continue

                # Check if already escalated to this channel
                log_stmt = select(NotificationLog).where(
                    NotificationLog.alert_id == alert.id,
                    NotificationLog.channel_id == rule.channel_id,
                    NotificationLog.is_escalation,
                )
                log_res = await session.execute(log_stmt)
                if log_res.scalar_one_or_none():
                    continue

                log.info("alert_escalating", alert_id=alert.id, channel_id=rule.channel_id)
                await route_alert(session, alert.id, is_escalation=True)

            # 2. Evaluate open Incidents
            incidents_stmt = (
                select(Incident)
                .options(selectinload(Incident.alerts))
                .where(
                    Incident.status == "open",
                    Incident.first_seen <= cutoff_naive,
                )
            )
            incidents_res = await session.execute(incidents_stmt)
            incidents = incidents_res.scalars().all()

            for incident in incidents:
                if not matches_criteria(rule, incident):
                    continue

                # Check if already escalated to this channel
                log_stmt = select(NotificationLog).where(
                    NotificationLog.incident_id == incident.id,
                    NotificationLog.channel_id == rule.channel_id,
                    NotificationLog.is_escalation,
                )
                log_res = await session.execute(log_stmt)
                if log_res.scalar_one_or_none():
                    continue

                log.info("incident_escalating", incident_id=incident.id, channel_id=rule.channel_id)
                await route_incident(session, incident.id, is_escalation=True)


async def escalation_loop() -> None:
    """Infinite loop for the escalation worker running periodically."""
    log.info("escalation_worker_started", interval_seconds=30)
    while _running:
        try:
            await check_escalations()
        except Exception as exc:
            log.error("escalation_worker_loop_error", error=str(exc))
        
        # Sleep for 30 seconds before next evaluation round
        await asyncio.sleep(30)


def start_escalation_worker() -> None:
    """Start background escalation worker task."""
    global _escalation_task, _running
    if _running:
        return
    _running = True
    _escalation_task = asyncio.create_task(escalation_loop())
    log.info("escalation_worker_scheduled")


async def stop_escalation_worker() -> None:
    """Stop background escalation worker and cancel task."""
    global _escalation_task, _running
    if not _running:
        return
    _running = False
    if _escalation_task:
        _escalation_task.cancel()
        try:
            await _escalation_task
        except asyncio.CancelledError:
            pass
        _escalation_task = None
    log.info("escalation_worker_stopped")
