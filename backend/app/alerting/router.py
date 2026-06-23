"""Notification Router pipeline.

Evaluates routing rules, silences, deduplication, and rate limiting,
then renders templates and dispatches alerts/incidents to target channels.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.alerting.channels import get_channel_instance
from app.alerting.ratelimit import check_rate_limit
from app.alerting.silence import is_silenced
from app.alerting.templates import render_alert_notification, render_incident_notification
from app.core import metadata_db
from app.core.logging import get_logger
from app.models.alert import Alert
from app.models.channel import Channel
from app.models.incident import Incident
from app.models.notification_log import NotificationLog
from app.models.routing_rule import RoutingRule

log = get_logger("sentinel.alerting.router")

DEDUP_WINDOW_SECONDS = 300  # 5 minutes

_background_tasks: set[asyncio.Task[Any]] = set()


def matches_criteria(rule: RoutingRule, target: Alert | Incident) -> bool:
    """Evaluate if an Alert or Incident matches the routing rule criteria."""
    criteria = rule.criteria or {}
    if not criteria:
        # Match-all rule
        return True

    # 1. Match severity
    if criteria.get("severities"):
        rule_sevs = [s.lower() for s in criteria["severities"]]
        if target.severity.lower() not in rule_sevs:
            return False

    # 2. Match rule_ids (mostly for Alerts, or Incidents with matching alerts)
    if criteria.get("rule_ids"):
        if isinstance(target, Alert):
            if target.rule_id not in criteria["rule_ids"]:
                return False
        elif isinstance(target, Incident):
            try:
                alert_rules = {a.rule_id for a in target.alerts}
                if not any(r in alert_rules for r in criteria["rule_ids"]):
                    return False
            except Exception:
                return False

    # 3. Match tags (Sigma rule MITRE ATT&CK tags)
    if criteria.get("tags"):
        rule_tags = [t.lower() for t in criteria["tags"]]
        target_tags = set()
        if isinstance(target, Alert):
            for m in target.mitre_mapping:
                if m.get("technique_id"):
                    target_tags.add(m["technique_id"].lower())
        elif isinstance(target, Incident):
            try:
                for a in target.alerts:
                    for m in a.mitre_mapping:
                        if m.get("technique_id"):
                            target_tags.add(m["technique_id"].lower())
            except Exception as e:
                log.debug("incident_alerts_tag_extraction_failed", error=str(e))

        if not any(rt in target_tags for rt in rule_tags):
            return False

    return True


async def check_deduplication(
    db: AsyncSession,
    target: Alert | Incident,
    channel_id: int,
    window_seconds: int = DEDUP_WINDOW_SECONDS,
) -> bool:
    """Verify if a notification was already sent to this channel within the window."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=window_seconds)

    stmt = select(NotificationLog).where(
        NotificationLog.channel_id == channel_id,
        NotificationLog.status == "sent",
    )
    if isinstance(target, Alert):
        stmt = stmt.where(NotificationLog.alert_id == target.id)
    else:
        stmt = stmt.where(NotificationLog.incident_id == target.id)

    res = await db.execute(stmt)
    logs = res.scalars().all()

    for entry in logs:
        sent_at = entry.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=UTC)
        if sent_at >= cutoff:
            return True

    return False


async def send_notification(
    channel: Channel,
    message: str,
    subject: str,
    alert_id: int | None = None,
    incident_id: int | None = None,
    is_escalation: bool = False,
) -> bool:
    """Send notification via channel with retries, using an independent DB session.

    Opens its own session so it is safe to run inside asyncio.create_task after
    the caller's session has already been closed.
    """
    try:
        sender = get_channel_instance(channel.type, channel.config)
    except Exception as exc:
        log.error("channel_instantiation_failed", channel_id=channel.id, error=str(exc))
        async with metadata_db.AsyncSessionLocal() as db:
            db.add(NotificationLog(
                alert_id=alert_id,
                incident_id=incident_id,
                channel_id=channel.id,
                status="failed",
                error_message=f"Instantiation failed: {exc}",
                is_escalation=is_escalation,
                retry_count=0,
            ))
            await db.commit()
        return False

    max_retries = 3
    success = False
    error_msg = None
    attempt = 0

    for attempt in range(max_retries):
        try:
            await sender.send(message, subject=subject)
            success = True
            break
        except Exception as exc:
            error_msg = str(exc)
            log.warning(
                "notification_send_attempt_failed",
                channel_id=channel.id,
                attempt=attempt + 1,
                error=error_msg,
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)

    async with metadata_db.AsyncSessionLocal() as db:
        db.add(NotificationLog(
            alert_id=alert_id,
            incident_id=incident_id,
            channel_id=channel.id,
            status="sent" if success else "failed",
            error_message=None if success else error_msg,
            is_escalation=is_escalation,
            retry_count=attempt,
        ))
        await db.commit()
    return success



async def route_alert(db: AsyncSession, alert_id: int, is_escalation: bool = False) -> None:
    """Route an Alert to matching channels."""
    # Eager load mitre mapping/relations
    stmt = select(Alert).where(Alert.id == alert_id)
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        log.error("route_alert_not_found", alert_id=alert_id)
        return

    # Check silence rules
    if await is_silenced(db, alert):
        log.info("alert_silenced", alert_id=alert_id)
        # Log muting event
        return

    # Fetch active routing rules
    rules_stmt = (
        select(RoutingRule)
        .options(selectinload(RoutingRule.channel))
        .where(RoutingRule.is_active)
    )
    rules_res = await db.execute(rules_stmt)
    rules = rules_res.scalars().all()

    for rule in rules:
        # For escalation worker: skip non-escalation or rule mismatch
        if is_escalation and rule.escalation_delay_min is None:
            continue

        if not matches_criteria(rule, alert):
            continue

        channel = rule.channel
        if not channel or not channel.is_active:
            continue

        # 1. Deduplication
        if await check_deduplication(db, alert, channel.id):
            log.info("alert_notification_deduplicated", alert_id=alert_id, channel_id=channel.id)
            n_log = NotificationLog(
                alert_id=alert_id,
                channel_id=channel.id,
                status="skipped_dedup",
                is_escalation=is_escalation,
            )
            db.add(n_log)
            await db.commit()
            continue

        # 2. Rate limiting
        if not check_rate_limit(channel.id):
            log.warn("alert_notification_rate_limited", alert_id=alert_id, channel_id=channel.id)
            n_log = NotificationLog(
                alert_id=alert_id,
                channel_id=channel.id,
                status="rate_limited",
                is_escalation=is_escalation,
            )
            db.add(n_log)
            await db.commit()
            continue

        # 3. Render template
        custom_template = channel.config.get("template")
        try:
            rendered = render_alert_notification(alert, custom_template)
        except Exception as exc:
            log.error("alert_template_rendering_failed", alert_id=alert_id, error=str(exc))
            continue

        subject = f"🔔 [{alert.severity.upper()}] Alert: {alert.rule_name}"
        if is_escalation:
            subject = f"⚠️ [ESCALATION] {subject}"

        # 4. Dispatch async — send_notification manages its own session
        task = asyncio.create_task(
            send_notification(
                channel=channel,
                message=rendered,
                subject=subject,
                alert_id=alert_id,
                is_escalation=is_escalation,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)


async def route_incident(db: AsyncSession, incident_id: int, is_escalation: bool = False) -> None:
    """Route an Incident to matching channels."""
    stmt = (
        select(Incident)
        .options(selectinload(Incident.alerts))
        .where(Incident.id == incident_id)
    )
    res = await db.execute(stmt)
    incident = res.scalar_one_or_none()
    if not incident:
        log.error("route_incident_not_found", incident_id=incident_id)
        return

    # Check silence rules
    if await is_silenced(db, incident):
        log.info("incident_silenced", incident_id=incident_id)
        return

    # Fetch active routing rules
    rules_stmt = (
        select(RoutingRule)
        .options(selectinload(RoutingRule.channel))
        .where(RoutingRule.is_active)
    )
    rules_res = await db.execute(rules_stmt)
    rules = rules_res.scalars().all()

    for rule in rules:
        if is_escalation and rule.escalation_delay_min is None:
            continue

        if not matches_criteria(rule, incident):
            continue

        channel = rule.channel
        if not channel or not channel.is_active:
            continue

        # 1. Deduplication
        if await check_deduplication(db, incident, channel.id):
            log.info(
                "incident_notification_deduplicated",
                incident_id=incident_id,
                channel_id=channel.id,
            )
            n_log = NotificationLog(
                incident_id=incident_id,
                channel_id=channel.id,
                status="skipped_dedup",
                is_escalation=is_escalation,
            )
            db.add(n_log)
            await db.commit()
            continue

        # 2. Rate limiting
        if not check_rate_limit(channel.id):
            log.warn(
                "incident_notification_rate_limited",
                incident_id=incident_id,
                channel_id=channel.id,
            )
            n_log = NotificationLog(
                incident_id=incident_id,
                channel_id=channel.id,
                status="rate_limited",
                is_escalation=is_escalation,
            )
            db.add(n_log)
            await db.commit()
            continue

        # 3. Render template
        custom_template = channel.config.get("template")
        try:
            rendered = render_incident_notification(incident, custom_template)
        except Exception as exc:
            log.error("incident_template_rendering_failed", incident_id=incident_id, error=str(exc))
            continue

        subject = f"🚨 [{incident.severity.upper()}] Incident: {incident.title}"
        if is_escalation:
            subject = f"⚠️ [ESCALATION] {subject}"

        # 4. Dispatch async — send_notification manages its own session
        task = asyncio.create_task(
            send_notification(
                channel=channel,
                message=rendered,
                subject=subject,
                incident_id=incident_id,
                is_escalation=is_escalation,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
