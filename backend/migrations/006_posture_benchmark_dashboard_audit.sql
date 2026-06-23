-- target: sqlite
-- Phase 7: posture runs, benchmark runs, dashboard layouts, audit log.
-- Tables are also created by SQLAlchemy create_all; this file documents the schema.

CREATE TABLE IF NOT EXISTS posture_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tool VARCHAR(50) NOT NULL,            -- trivy, lynis
    score REAL NOT NULL,                  -- 0..100 CIS-style
    drift REAL NOT NULL DEFAULT 0,        -- delta vs previous run
    findings TEXT NOT NULL,               -- JSON
    total_findings INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scenario VARCHAR(50) NOT NULL,        -- ingest_throughput, query_latency
    metric_value REAL NOT NULL,
    metric_unit VARCHAR(20) NOT NULL,
    passed BOOLEAN NOT NULL DEFAULT 0,
    raw_summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dashboard_layouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner VARCHAR(255) NOT NULL UNIQUE,
    widgets TEXT NOT NULL,                -- JSON [{id,type,title,query,x,y,w,h}]
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(255) NOT NULL DEFAULT 'anonymous',
    method VARCHAR(10) NOT NULL,
    path VARCHAR(512) NOT NULL,
    status_code INTEGER NOT NULL
);
