"""Sentinel backend FastAPI application.

Phase 0: exposes ``/healthz`` (dependency-aware) and ``/metrics`` (Prometheus).
Later phases mount routers under ``app/api`` onto this app.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import __version__
from app.alerting.escalation import start_escalation_worker, stop_escalation_worker
from app.api import ai as ai_api
from app.api import alerts as alerts_api
from app.api import audit as audit_api
from app.api import benchmark as benchmark_api
from app.api import channels as channels_api
from app.api import connectors as connectors_api
from app.api import dashboard as dashboard_api
from app.api import events as events_api
from app.api import incidents as incidents_api
from app.api import ingest_webhook as ingest_webhook_api
from app.api import playbooks as playbooks_api
from app.api import posture as posture_api
from app.connectors.manager import manager as connector_manager
from app.core import clickhouse
from app.core.audit import AuditMiddleware
from app.core.config import settings
from app.core.health import gather_health
from app.core.logging import configure_logging, get_logger
from app.core.metadata_db import init_db
from app.detection.scheduler import start_scheduler, stop_scheduler
from app.ingest.consumer import consumer
from app.ingest.producer import producer
from app.soar.triggers import start_cron_worker, stop_cron_worker

configure_logging(settings.log_level)
log = get_logger("sentinel.main")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info("startup", app=settings.app_name, env=settings.environment, version=__version__)
    
    # Initialize SQLite metadata database schemas
    try:
        await init_db()
        log.info("metadata_db_initialized")
    except Exception as exc:
        log.error("metadata_db_init_failed", error=str(exc))

    if settings.ingest_enabled:
        try:
            await clickhouse.run_migrations()
        except Exception as exc:  # migrations are best-effort at boot; surfaced via /healthz
            log.error("migrations_failed", error=str(exc))
        await consumer.start()
        # Producer feeds the same events topic; connectors + webhook-IN publish through it.
        await producer.start()
        await connector_manager.start()

    # Start detection scheduler, escalation worker and SOAR cron worker
    start_scheduler()
    start_escalation_worker()
    start_cron_worker()

    yield

    # Stop scheduler, workers, connectors, producer and consumer
    await stop_cron_worker()
    await stop_escalation_worker()
    await stop_scheduler()
    await connector_manager.stop()
    await producer.stop()
    await consumer.stop()
    log.info("shutdown", app=settings.app_name)


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
app.include_router(events_api.router)
app.include_router(alerts_api.router)
app.include_router(incidents_api.router)
app.include_router(channels_api.router)
app.include_router(ai_api.router)
app.include_router(connectors_api.router)
app.include_router(ingest_webhook_api.router)
app.include_router(playbooks_api.router)
app.include_router(posture_api.router)
app.include_router(benchmark_api.router)
app.include_router(dashboard_api.router)
app.include_router(audit_api.router)


# Audit every mutating request centrally (appended to audit_log).
app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, object]:
    """Liveness + dependency readiness. Always 200; body carries status."""
    return await gather_health()


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus exposition format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
