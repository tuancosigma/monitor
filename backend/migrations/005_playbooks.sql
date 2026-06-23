-- target: sqlite
-- Phase 6: SOAR playbooks (DAG trigger->action) + run audit.
-- Tables are also created by SQLAlchemy create_all; this file documents the schema.

CREATE TABLE IF NOT EXISTS playbooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    trigger_type VARCHAR(50) NOT NULL,   -- alert, incident, cron, webhook
    trigger_filter TEXT NOT NULL,        -- JSON subset-match criteria
    nodes TEXT NOT NULL,                 -- JSON [{id, action, params}]
    edges TEXT NOT NULL,                 -- JSON [[from_id, to_id]]
    auto_approve BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playbook_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playbook_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- success/failed/dry_run/blocked
    dry_run BOOLEAN NOT NULL DEFAULT 0,
    trigger_context TEXT NOT NULL,       -- JSON
    node_results TEXT NOT NULL,          -- JSON [{node_id, action, status, output}]
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP NULL,
    node_count INTEGER NOT NULL DEFAULT 0
);
