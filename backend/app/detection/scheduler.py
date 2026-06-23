"""Scheduled Sigma rule evaluator task.

Periodically queries ClickHouse for matching log events, dedupes alerts,
and correlates matches into Incidents.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clickhouse
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metadata_db import AsyncSessionLocal
from app.detection.clickhouse_backend import FIELD_MAPPING, compile_sigma_rule
from app.detection.correlation import correlate_alert
from app.detection.sigma_loader import SigmaRule, load_rules_from_dir
from app.models.alert import Alert
from app.models.incident import Incident

log = get_logger("sentinel.scheduler")

SAMPLE_KEYS = [
    "timestamp",
    "message",
    "host_name",
    "user_name",
    "source_ip",
    "destination_ip",
    "event_category",
    "event_outcome",
]

_scheduler_task: asyncio.Task[None] | None = None
_running = False


def parse_timeframe_to_seconds(timeframe: str | None) -> int:
    """Parse timeframe string (e.g., '1m', '5m', '12h') into seconds."""
    if not timeframe:
        return 300  # Default to 5 minutes lookback

    # Separate digits and letters
    val_str = "".join(c for c in timeframe if c.isdigit())
    unit_str = "".join(c for c in timeframe if c.isalpha()).lower()

    if not val_str:
        return 300

    val = int(val_str)
    if unit_str == "s":
        return val
    elif unit_str == "m":
        return val * 60
    elif unit_str == "h":
        return val * 3600
    elif unit_str == "d":
        return val * 86400

    return 300


async def evaluate_rule(
    rule: SigmaRule, db: AsyncSession, eval_time: datetime
) -> tuple[list[Alert], list[Incident]]:
    """Evaluate a single Sigma rule against ClickHouse and ingest any alerts."""
    new_alerts: list[Alert] = []
    new_incidents: list[Incident] = []

    # 1. Lookback timeframe
    timeframe_sec = parse_timeframe_to_seconds(rule.detection.timeframe)
    # We query from (eval_time - timeframe) to eval_time
    start_time = eval_time - timedelta(seconds=timeframe_sec)
    end_time = eval_time

    # 2. Compile to parameterized ClickHouse SQL
    sql, params = compile_sigma_rule(rule)

    # 3. Add base parameters
    params["start_time"] = start_time
    params["end_time"] = end_time

    # 4. Execute ClickHouse query
    result = await clickhouse.execute(sql, params)
    rows = result.result_rows

    if not rows:
        return new_alerts, new_incidents

    # 5. Process matches
    if rule.detection.count:
        # Aggregation Rule: rows are [(entity_val, cnt, samples), ...]
        count_field = rule.detection.count.get("field")
        entity_type = "unknown"
        if count_field:
            mapped_col = FIELD_MAPPING.get(count_field.lower(), count_field.lower())
            if "ip" in mapped_col:
                entity_type = "ip"
            elif "user" in mapped_col:
                entity_type = "username"
            elif "host" in mapped_col:
                entity_type = "hostname"

        for row in rows:
            entity_val = str(row[0]) if row[0] is not None else ""
            int(row[1])
            raw_samples = row[2]

            # Coerce samples list to nice JSON dictionary format
            samples_list = []
            for sample in raw_samples:
                # sample is a tuple matching fields in SAMPLE_KEYS
                sample_dict = {}
                for k, v in zip(SAMPLE_KEYS, sample, strict=False):
                    if isinstance(v, datetime):
                        sample_dict[k] = v.isoformat()
                    else:
                        sample_dict[k] = v
                samples_list.append(sample_dict)

            # Deduplication key based on rule_id, entity value and timeframe bucket
            time_bucket = int(eval_time.timestamp() / timeframe_sec) * timeframe_sec
            dedup_key_raw = f"{rule.id}:{entity_val}:{time_bucket}"
            dedup_key = hashlib.sha256(dedup_key_raw.encode("utf-8")).hexdigest()[:32]

            # Check if alert already exists
            existing = await db.execute(select(Alert).where(Alert.dedup_key == dedup_key))
            if existing.scalar_one_or_none():
                continue

            # Create Alert
            entities = [{"type": entity_type, "value": entity_val}] if entity_val else []
            alert = Alert(
                rule_id=rule.id,
                rule_name=rule.title,
                severity=rule.severity,
                status="open",
                timestamp=eval_time,
                dedup_key=dedup_key,
                entities=entities,
                mitre_mapping=rule.get_mitre_mappings(),
                sample_events=samples_list,
            )
            db.add(alert)
            await db.flush()
            new_alerts.append(alert)

            # Correlate Alert into Incidents
            incident, is_new = await correlate_alert(db, alert)
            if is_new:
                new_incidents.append(incident)

    else:
        # Simple rule: rows are raw matching logs
        for row in rows:
            # row represents a single event: timestamp, message, host_name, user_name,
            # source_ip, destination_ip, event_category, event_outcome
            event = dict(zip(SAMPLE_KEYS, row, strict=False))

            # Coerce timestamp to string for dedup key hashing
            event_ts = event.get("timestamp")
            if isinstance(event_ts, datetime):
                # Ensure tz-aware
                if event_ts.tzinfo is None:
                    event_ts = event_ts.replace(tzinfo=UTC)
                ts_str = event_ts.isoformat()
            else:
                ts_str = str(event_ts)

            # Generate unique hash of event key details
            hash_str = (
                f"{ts_str}:{event.get('host_name')}:"
                f"{event.get('user_name')}:{event.get('message')}"
            )
            event_hash = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()[:16]
            dedup_key = f"{rule.id}:{event_hash}"

            # Check if alert already exists
            existing = await db.execute(select(Alert).where(Alert.dedup_key == dedup_key))
            if existing.scalar_one_or_none():
                continue

            # Serialize datetimes in event dict to strings
            event_clean = {}
            for k, v in event.items():
                if isinstance(v, datetime):
                    event_clean[k] = v.isoformat()
                else:
                    event_clean[k] = v

            alert = Alert(
                rule_id=rule.id,
                rule_name=rule.title,
                severity=rule.severity,
                status="open",
                timestamp=event_ts if isinstance(event_ts, datetime) else eval_time,
                dedup_key=dedup_key,
                entities=[],  # Will be extracted inside correlate_alert
                mitre_mapping=rule.get_mitre_mappings(),
                sample_events=[event_clean],
            )
            db.add(alert)
            await db.flush()
            new_alerts.append(alert)

            # Correlate Alert into Incidents
            incident, is_new = await correlate_alert(db, alert)
            if is_new:
                new_incidents.append(incident)

    return new_alerts, new_incidents



async def evaluation_loop() -> None:
    """Infinite loop evaluating Sigma rules periodically."""
    log.info("detection_scheduler_started", interval_seconds=10)
    while _running:
        try:
            eval_time = datetime.now(UTC)
            rules = load_rules_from_dir(settings.rules_dir)
            if rules:
                all_new_alerts: list[Alert] = []
                all_new_incidents: list[Incident] = []
                # We open an async database session for this batch evaluation
                async with AsyncSessionLocal() as session:
                    for rule in rules:
                        try:
                            # Evaluate each rule in isolation
                            rule_alerts, rule_incidents = await evaluate_rule(
                                rule, session, eval_time
                            )
                            all_new_alerts.extend(rule_alerts)
                            all_new_incidents.extend(rule_incidents)
                        except Exception as exc:
                            log.error(
                                "rule_evaluation_failed",
                                rule_id=rule.id,
                                rule_name=rule.title,
                                error=str(exc),
                            )
                    await session.commit()

                # Dispatch notifications + SOAR playbooks after commit
                if all_new_alerts or all_new_incidents:
                    from app.alerting.router import route_alert, route_incident
                    from app.soar.triggers import fire as fire_playbooks
                    for alert in all_new_alerts:
                        try:
                            async with AsyncSessionLocal() as route_session:
                                await route_alert(route_session, alert.id)
                            await fire_playbooks(
                                "alert",
                                {"type": "alert", "id": alert.id,
                                 "severity": alert.severity, "rule_id": alert.rule_id},
                            )
                        except Exception as exc:
                            log.error("route_alert_failed", alert_id=alert.id, error=str(exc))
                    for incident in all_new_incidents:
                        try:
                            async with AsyncSessionLocal() as route_session:
                                await route_incident(route_session, incident.id)
                            await fire_playbooks(
                                "incident",
                                {"type": "incident", "id": incident.id,
                                 "severity": incident.severity},
                            )
                        except Exception as exc:
                            log.error(
                                "route_incident_failed", incident_id=incident.id, error=str(exc)
                            )


        except Exception as exc:
            log.error("scheduler_loop_error", error=str(exc))

        # Sleep for 10 seconds before next evaluation round
        await asyncio.sleep(10)


def start_scheduler() -> None:
    """Start background scheduler loop."""
    global _scheduler_task, _running
    if _running:
        return
    _running = True
    _scheduler_task = asyncio.create_task(evaluation_loop())
    log.info("detection_scheduler_scheduled")


async def stop_scheduler() -> None:
    """Stop background scheduler loop and cancel the task."""
    global _scheduler_task, _running
    if not _running:
        return
    _running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
    log.info("detection_scheduler_stopped")
