"""Integration test for the notification routing pipeline.

Tests that rules match correctly, templates render, logs are generated,
and silences/deduplication prevent sending.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.alerting.router import route_alert
from app.core import metadata_db
from app.core.config import settings
from app.core.metadata_db import Base
from app.models.alert import Alert
from app.models.channel import Channel
from app.models.notification_log import NotificationLog
from app.models.routing_rule import RoutingRule
from app.models.silence import Silence


@pytest.fixture(autouse=True)
async def setup_metadata_db() -> AsyncIterator[None]:
    """Replace the global metadata_db engine/session with an isolated temp-file SQLite DB."""
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()

    old_url = settings.metadata_db_url
    settings.metadata_db_url = f"sqlite+aiosqlite:///{db_file.name}"

    old_engine = metadata_db.engine
    old_sessionmaker = metadata_db.AsyncSessionLocal

    # Rebuild engine and session factory on the module so every consumer of
    # `metadata_db.AsyncSessionLocal` (including router.py) uses this engine.
    metadata_db.engine = create_async_engine(
        settings.metadata_db_url,
        connect_args={"check_same_thread": False},
    )
    metadata_db.AsyncSessionLocal = async_sessionmaker(
        bind=metadata_db.engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create all tables on the new engine
    async with metadata_db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Restore global state
    await metadata_db.engine.dispose()
    metadata_db.engine = old_engine
    metadata_db.AsyncSessionLocal = old_sessionmaker
    settings.metadata_db_url = old_url

    try:
        os.unlink(db_file.name)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_alert_routing_integration() -> None:
    """Test full alert routing, matching criteria, and log persistence."""
    async with metadata_db.AsyncSessionLocal() as session:
        # 1. Create Slack notification channel
        channel = Channel(
            name="Slack SOC Channel",
            type="slack",
            config={"webhook_url": "https://hooks.slack.com/services/T00/B00/X00"},
            is_active=True,
        )
        session.add(channel)
        await session.commit()
        await session.refresh(channel)

        # 2. Create routing rule for high/critical alerts
        rule = RoutingRule(
            name="SOC Route Rule",
            criteria={"severities": ["critical", "high"]},
            channel_id=channel.id,
            is_active=True,
        )
        session.add(rule)

        # 3. Create active Silence rule that will NOT match the critical alert below
        silence = Silence(
            name="Silence Low Alerts Only",
            filters={"severity": "low"},
            start_time=datetime.now(UTC) - timedelta(hours=1),
            end_time=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        session.add(silence)
        await session.commit()

        # 4. Create sample Alert (critical — should match rule and be sent)
        alert = Alert(
            rule_id="rule-1",
            rule_name="Critical CPU Spike",
            severity="critical",
            status="open",
            timestamp=datetime.now(UTC),
            dedup_key="cpu-spike-1",
            entities=[{"type": "hostname", "value": "prod-web-01"}],
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)

    alert_id = alert.id
    channel_id = channel.id

    # 5. Route alert with SlackChannel.send mocked to avoid real HTTP calls
    with patch(
        "app.alerting.channels.slack.SlackChannel.send",
        new_callable=AsyncMock,
    ) as mock_send:
        async with metadata_db.AsyncSessionLocal() as session:
            await route_alert(session, alert_id)
            # Allow the asyncio.create_task() inside route_alert to run
            await asyncio.sleep(0.5)

        mock_send.assert_called_once()
        rendered_msg = mock_send.call_args[0][0]
        assert "🔔 [CRITICAL] Alert: Critical CPU Spike" in rendered_msg
        assert "prod-web-01" in rendered_msg

    # 6. Verify NotificationLog was persisted
    async with metadata_db.AsyncSessionLocal() as session:
        res = await session.execute(select(NotificationLog))
        logs = res.scalars().all()
        assert len(logs) == 1
        log_entry = logs[0]
        assert log_entry.alert_id == alert_id
        assert log_entry.channel_id == channel_id
        assert log_entry.status == "sent"
        assert log_entry.is_escalation is False

    # 7. Route same alert again — must be skipped by deduplication
    with patch(
        "app.alerting.channels.slack.SlackChannel.send",
        new_callable=AsyncMock,
    ) as mock_send2:
        async with metadata_db.AsyncSessionLocal() as session:
            await route_alert(session, alert_id)
            await asyncio.sleep(0.5)

        mock_send2.assert_not_called()

    # 8. Verify the dedup-skip log entry was recorded
    async with metadata_db.AsyncSessionLocal() as session:
        res = await session.execute(
            select(NotificationLog).where(NotificationLog.status == "skipped_dedup")
        )
        assert res.scalar_one_or_none() is not None
