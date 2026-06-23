-- target: sqlite
-- Phase 3: Channels, Routing Rules, Silences, and Notification Logs.

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config TEXT NOT NULL, -- JSON formatted string
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS routing_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    criteria TEXT NOT NULL, -- JSON formatted string
    channel_id INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    escalation_delay_min INTEGER NULL,
    FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS silences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NULL,
    filters TEXT NOT NULL, -- JSON formatted string
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NULL,
    incident_id INTEGER NULL,
    channel_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT NULL,
    is_escalation BOOLEAN NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(alert_id) REFERENCES alerts(id) ON DELETE SET NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE SET NULL,
    FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
);
