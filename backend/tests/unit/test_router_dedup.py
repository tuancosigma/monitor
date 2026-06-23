"""Unit tests for Alerting templates, SSRF guard, rate-limiting, and silencing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.alerting.ratelimit import _channel_buckets, check_rate_limit
from app.alerting.silence import is_silenced
from app.alerting.templates import render_alert_notification, render_incident_notification
from app.core.metadata_db import Base
from app.core.ssrf_guard import is_safe_ip
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.silence import Silence


def test_ssrf_ip_validation() -> None:
    """Verify that private and loopback IPs are blocked while public IPs are allowed."""
    assert is_safe_ip("8.8.8.8") is True
    assert is_safe_ip("142.250.190.46") is True
    
    assert is_safe_ip("127.0.0.1") is False
    assert is_safe_ip("10.0.0.5") is False
    assert is_safe_ip("192.168.1.1") is False
    assert is_safe_ip("169.254.169.254") is False
    assert is_safe_ip("::1") is False


def test_sandboxed_alert_rendering() -> None:
    """Verify sandboxed Jinja rendering works correctly for Alert objects."""
    alert = Alert(
        id=42,
        rule_id="ssh-bruteforce",
        rule_name="SSH Brute Force Attack",
        severity="critical",
        status="open",
        timestamp=datetime(2026, 6, 23, 12, 0, 0, tzinfo=UTC),
        entities=[{"type": "ip", "value": "192.168.1.50"}],
        mitre_mapping=[{
            "tactic": "Credential Access",
            "technique_id": "T1110",
            "technique_name": "Brute Force",
        }],
    )
    rendered = render_alert_notification(alert)
    assert "🔔 [CRITICAL] Alert: SSH Brute Force Attack" in rendered
    assert "Status: open" in rendered
    assert "Rule ID: ssh-bruteforce" in rendered
    assert "ip: 192.168.1.50" in rendered
    assert "Credential Access (T1110): Brute Force" in rendered


def test_sandboxed_incident_rendering() -> None:
    """Verify sandboxed Jinja rendering works correctly for Incident objects."""
    incident = Incident(
        id=99,
        title="Security Incident: SSH brute force from IP 192.168.1.50",
        description="SSH Brute Force Attack triggered",
        severity="high",
        status="open",
        first_seen=datetime(2026, 6, 23, 12, 0, 0, tzinfo=UTC),
        last_seen=datetime(2026, 6, 23, 12, 5, 0, tzinfo=UTC),
        entities=[{"type": "ip", "value": "192.168.1.50"}],
    )
    rendered = render_incident_notification(incident)
    assert "🚨 [HIGH] Incident: Security Incident: SSH brute force from IP 192.168.1.50" in rendered
    assert "Status: open" in rendered
    assert "ip: 192.168.1.50" in rendered


def test_rate_limiting() -> None:
    """Verify token bucket rate limiter blocks requests exceeding capacity."""
    channel_id = 999
    # Reset bucket state
    if channel_id in _channel_buckets:
        del _channel_buckets[channel_id]

    # Max capacity is 3 for test, refill is 0.1 tokens/sec
    # We should be able to consume 3 immediately, but 4th fails
    assert check_rate_limit(channel_id, capacity=3.0, refill_rate=0.1) is True
    assert check_rate_limit(channel_id, capacity=3.0, refill_rate=0.1) is True
    assert check_rate_limit(channel_id, capacity=3.0, refill_rate=0.1) is True
    assert check_rate_limit(channel_id, capacity=3.0, refill_rate=0.1) is False


@pytest.fixture
async def test_db() -> AsyncSession:
    """Create in-memory SQLite database session for unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        
    await engine.dispose()


@pytest.mark.asyncio
async def test_silence_muting(test_db: AsyncSession) -> None:
    """Verify silence mute matching rules work correctly."""
    # 1. Create a silence muting rule for critical severity
    now = datetime.now(UTC)
    silence = Silence(
        name="Mute Critical Alerts",
        filters={"severity": "critical"},
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        is_active=True,
    )
    test_db.add(silence)
    await test_db.commit()

    # 2. Verify critical alert is silenced
    alert_critical = Alert(
        id=1,
        rule_id="rule-a",
        rule_name="Rule A",
        severity="critical",
        status="open",
        timestamp=now,
        dedup_key="key-a",
    )
    assert await is_silenced(test_db, alert_critical) is True

    # 3. Verify high alert is NOT silenced
    alert_high = Alert(
        id=2,
        rule_id="rule-b",
        rule_name="Rule B",
        severity="high",
        status="open",
        timestamp=now,
        dedup_key="key-b",
    )
    assert await is_silenced(test_db, alert_high) is False
