"""Connector model (SQLAlchemy + Pydantic): config + cursor + runtime status.

Secrets in ``config`` are env-references (e.g. {"api_key": "${WAZUH_KEY}"}) resolved
at runtime; raw secret values are never returned by the API.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metadata_db import Base


class Connector(Base):
    """Connector SQLAlchemy model."""

    __tablename__ = "connectors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # type options: wazuh, prometheus
    type: Mapped[str] = mapped_column(String(50), index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # opaque cursor (per-connector meaning, e.g. last alert timestamp / id)
    cursor: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="idle")  # idle/running/error
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


# ============================================================================
# Pydantic Schemas
# ============================================================================

_SECRET_KEYS = ("api_key", "password", "token", "secret")


def redact_config(config: dict[str, Any]) -> dict[str, Any]:
    """Mask secret-looking values that are not env-references, for API responses."""
    out: dict[str, Any] = {}
    for k, v in config.items():
        is_secret = any(s in k.lower() for s in _SECRET_KEYS)
        is_env_ref = isinstance(v, str) and v.startswith("${")
        out[k] = "***" if (is_secret and not is_env_ref) else v
    return out


class ConnectorBase(BaseModel):
    name: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ConnectorCreate(ConnectorBase):
    pass


class ConnectorUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class ConnectorResponse(ConnectorBase):
    id: int
    cursor: str | None = None
    status: str
    last_error: str | None = None
    last_run_at: datetime | None = None

    model_config = {"from_attributes": True}
