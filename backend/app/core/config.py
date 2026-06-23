"""Application settings sourced from environment variables.

Secrets and connection details are never hardcoded; all values come from the
environment (see ``.env.example``). Defaults are dev-safe but overridable.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object, instantiated once as ``settings``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SENTINEL_",
        extra="ignore",
    )

    # App metadata
    app_name: str = "sentinel-backend"
    environment: str = "dev"
    log_level: str = "INFO"

    # Background ingest consumer + migrations. Disabled in unit tests (no live stack).
    ingest_enabled: bool = True

    # Metadata DB (SQLite for stateful entities: alerts/incidents)
    metadata_db_url: str = "sqlite+aiosqlite:///metadata.db"
    rules_dir: str = "rules"

    # SOAR: script action is RCE-risky — disabled unless explicitly enabled.
    soar_script_enabled: bool = False

    # CORS — restrict browser access to the frontend origin only
    frontend_origin: str = "http://localhost:3000"

    # ClickHouse (event/log/metric storage)
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "sentinel"
    clickhouse_password: str = "sentinel"  # noqa: S105 — dev default, overridden via env
    clickhouse_database: str = "sentinel"

    # Redpanda (Kafka API) — ingest backbone
    kafka_bootstrap_servers: str = "redpanda:9092"
    kafka_events_topic: str = "events"
    kafka_dlq_topic: str = "events_dlq"

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_origin]


settings = Settings()
