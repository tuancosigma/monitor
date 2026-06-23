-- target: sqlite
-- Phase 5: external source connectors (Wazuh/Prometheus polled, webhook-IN push).
-- Tables are also created by SQLAlchemy create_all; this file documents the schema.

CREATE TABLE IF NOT EXISTS connectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,          -- wazuh, prometheus, webhook
    config TEXT NOT NULL,               -- JSON; secrets are ${ENV} references
    is_active BOOLEAN NOT NULL DEFAULT 1,
    cursor VARCHAR(512) NULL,           -- opaque per-connector poll cursor
    status VARCHAR(50) NOT NULL DEFAULT 'idle',
    last_error VARCHAR(1024) NULL,
    last_run_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
