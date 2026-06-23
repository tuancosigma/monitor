"""Integration test for Sigma detection scheduler, alert generation, and incident correlation.

Runs against an ephemeral ClickHouse container using testcontainers.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core import clickhouse as ch_mod
from app.core.config import settings
from app.core.metadata_db import AsyncSessionLocal
from app.detection.scheduler import evaluate_rule
from app.detection.sigma_loader import parse_sigma_rule
from app.ingest.clickhouse_writer import write_batch
from app.ingest.validate import parse_event
from app.models.alert import Alert
from app.models.incident import Incident

pytestmark = pytest.mark.skipif(
    os.environ.get("SENTINEL_INTEGRATION") != "1",
    reason="set SENTINEL_INTEGRATION=1 (needs Docker) to run integration tests",
)

testcontainers = pytest.importorskip("testcontainers.clickhouse")


@pytest.fixture(scope="module")
def clickhouse_url() -> Iterator[None]:
    from testcontainers.clickhouse import ClickHouseContainer

    with ClickHouseContainer("clickhouse/clickhouse-server:24.3") as ch:
        # Point settings to ephemeral ClickHouse container
        settings.clickhouse_host = ch.get_container_host_ip()
        settings.clickhouse_port = int(ch.get_exposed_port(8123))
        settings.clickhouse_user = ch.username
        settings.clickhouse_password = ch.password
        settings.clickhouse_database = ch.dbname
        ch_mod._client = None  # Force reconnection
        yield None
        ch_mod._client = None


@pytest.fixture(autouse=True)
async def setup_metadata_db() -> Iterator[None]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core import metadata_db

    # Use a temp file for SQLite to prevent collision
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    
    old_url = settings.metadata_db_url
    settings.metadata_db_url = f"sqlite+aiosqlite:///{db_file.name}"
    
    # Save old engine and SessionLocal
    old_engine = metadata_db.engine
    old_sessionmaker = metadata_db.AsyncSessionLocal
    
    # Recreate engine and sessionmaker on the existing module to preserve Base registry
    metadata_db.engine = create_async_engine(
        settings.metadata_db_url,
        connect_args={"check_same_thread": False},
    )
    metadata_db.AsyncSessionLocal = async_sessionmaker(
        bind=metadata_db.engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    await metadata_db.init_db()
    yield
    
    # Clean up and restore
    await metadata_db.engine.dispose()
    metadata_db.engine = old_engine
    metadata_db.AsyncSessionLocal = old_sessionmaker
    
    try:
        os.unlink(db_file.name)
    except OSError:
        pass
    settings.metadata_db_url = old_url


async def test_sigma_evaluation_and_correlation(clickhouse_url: None) -> None:
    # 1. Run migrations for the ephemeral ClickHouse
    await ch_mod.run_migrations()

    # 2. Parse the rule to test
    rule_yaml = """
    id: 5a8a478b-302a-4db5-b82b-8a8b13c7dbba
    title: SSH Brute Force Test
    severity: high
    tags:
      - attack.t1110
    detection:
      selection:
        event_category: authentication
        event_outcome: failure
      condition: selection
      timeframe: 1m
      count:
        field: source_ip
        op: gte
        value: 5
    """
    rule = parse_sigma_rule(rule_yaml)

    # 3. Seed 5 failed login events from 192.168.1.50, and 1 from 192.168.1.100
    eval_time = datetime.now(UTC)
    events = []
    
    # 5 failures from 192.168.1.50 (spaced by 5s to be strictly inside the 1m lookback window)
    for i in range(5):
        ts = (eval_time - timedelta(seconds=5 + 5 * i)).isoformat().replace("+00:00", "Z")
        evt = parse_event(
            f'{{"@timestamp":"{ts}","event.category":"authentication",'
            f'"event.outcome":"failure","source.ip":"192.168.1.50","host.name":"web-01"}}'
        )
        events.append(evt)

    # 1 failure from 192.168.1.100 (should not trigger the rule count threshold of 5)
    ts_other = (eval_time - timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
    evt_other = parse_event(
        f'{{"@timestamp":"{ts_other}","event.category":"authentication",'
        f'"event.outcome":"failure","source.ip":"192.168.1.100","host.name":"web-01"}}'
    )
    events.append(evt_other)

    await write_batch(events)

    # 4. Evaluate the rule using our scheduler helper
    async with AsyncSessionLocal() as session:
        await evaluate_rule(rule, session, eval_time)
        await session.commit()

    # 5. Check if alert and incident were created in SQLite
    async with AsyncSessionLocal() as session:
        # Verify Alert
        alert_res = await session.execute(
            select(Alert).options(selectinload(Alert.incident))
        )
        alerts = alert_res.scalars().all()
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.rule_id == rule.id
        assert alert.rule_name == "SSH Brute Force Test"
        assert alert.severity == "high"
        assert {"type": "ip", "value": "192.168.1.50"} in alert.entities
        assert {"type": "hostname", "value": "web-01"} in alert.entities
        assert alert.mitre_mapping == [
            {
                "tactic": "Credential Access",
                "technique_id": "T1110",
                "technique_name": "Brute Force",
            }
        ]
        assert len(alert.sample_events) == 5

        # Verify Incident
        incident_res = await session.execute(select(Incident))
        incidents = incident_res.scalars().all()
        assert len(incidents) == 1
        incident = incidents[0]
        assert incident.severity == "high"
        assert "SSH Brute Force Test" in incident.description
        assert alert.incident_id == incident.id

    # 6. Test Alert Deduplication (Evaluating again in the same window shouldn't create a new alert)
    async with AsyncSessionLocal() as session:
        await evaluate_rule(rule, session, eval_time)
        await session.commit()

    async with AsyncSessionLocal() as session:
        alerts = (await session.execute(select(Alert))).scalars().all()
        assert len(alerts) == 1  # Deduplicated!

    # 7. Test Incident Correlation: Add another alert for the same IP (different rule)
    rule_other_yaml = """
    id: dbf4e78b-302a-4db5-b82b-8a8b13c7dbba
    title: Secondary Threat
    severity: critical
    tags:
      - attack.t1078
    detection:
      selection:
        event_category: authentication
        event_outcome: success
      condition: selection
    """
    rule_other = parse_sigma_rule(rule_other_yaml)

    # Seed a successful login event from 192.168.1.50 (matches rule_other, inside lookback window)
    ts_success = (eval_time - timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
    evt_success = parse_event(
        f'{{"@timestamp":"{ts_success}","event.category":"authentication",'
        f'"event.outcome":"success","source.ip":"192.168.1.50","host.name":"web-01"}}'
    )
    await write_batch([evt_success])

    async with AsyncSessionLocal() as session:
        await evaluate_rule(rule_other, session, eval_time)
        await session.commit()

    async with AsyncSessionLocal() as session:
        alerts = (await session.execute(select(Alert))).scalars().all()
        # Should now have 2 alerts: SSH Brute Force and Secondary Threat
        assert len(alerts) == 2
        
        # Both alerts must belong to the same incident because they share IP 192.168.1.50
        incidents = (await session.execute(select(Incident))).scalars().all()
        assert len(incidents) == 1
        
        incident = incidents[0]
        # Severity should have upgraded from high to critical
        assert incident.severity == "critical"
        assert "SSH Brute Force Test" in incident.description
        assert "Secondary Threat" in incident.description
