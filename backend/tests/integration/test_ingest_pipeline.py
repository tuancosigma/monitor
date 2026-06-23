"""Integration test for the ClickHouse ingest path using a real ClickHouse container.

Skipped automatically when Docker/testcontainers are unavailable. Run with:
    SENTINEL_INTEGRATION=1 pytest tests/integration -q
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SENTINEL_INTEGRATION") != "1",
    reason="set SENTINEL_INTEGRATION=1 (needs Docker) to run integration tests",
)

testcontainers = pytest.importorskip("testcontainers.clickhouse")


@pytest.fixture(scope="module")
def clickhouse_url() -> Iterator[None]:
    from testcontainers.clickhouse import ClickHouseContainer

    with ClickHouseContainer("clickhouse/clickhouse-server:24.3") as ch:
        # Point the app's settings at the ephemeral container.
        from app.core import clickhouse as ch_mod
        from app.core.config import settings

        settings.clickhouse_host = ch.get_container_host_ip()
        settings.clickhouse_port = int(ch.get_exposed_port(8123))
        settings.clickhouse_user = ch.username
        settings.clickhouse_password = ch.password
        settings.clickhouse_database = ch.dbname
        ch_mod._client = None  # force reconnect against the container
        yield None
        ch_mod._client = None


async def test_valid_event_persists_and_bad_event_dead_letters(clickhouse_url: None) -> None:
    from app.core import clickhouse
    from app.ingest import clickhouse_writer, dlq
    from app.ingest.validate import ValidationFailure, parse_event

    await clickhouse.run_migrations()

    good = parse_event(
        '{"@timestamp":"2026-06-23T10:00:00Z","host.name":"web-01",'
        '"event.action":"ssh_login_failed","event.severity":70,"user.name":"root"}'
    )
    assert not isinstance(good, ValidationFailure)
    await clickhouse_writer.write_batch([good])

    bad = parse_event("{not-json")
    assert isinstance(bad, ValidationFailure)
    await dlq.record_failures([bad])

    events = await clickhouse.execute("SELECT count() FROM events WHERE host_name = 'web-01'")
    assert events.result_rows[0][0] == 1

    dead = await clickhouse.execute("SELECT count() FROM events_dlq")
    assert dead.result_rows[0][0] == 1
