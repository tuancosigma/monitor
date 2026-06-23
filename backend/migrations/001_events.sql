-- Phase 1: central events table (the cross-phase data contract) + dead-letter table.
-- Columns are the snake_case flattening of EcsEvent (see app/models/ecs_event.py).

CREATE TABLE IF NOT EXISTS events
(
    `@timestamp`                  DateTime64(3, 'UTC'),
    event_kind                    LowCardinality(String),
    event_category                LowCardinality(String) DEFAULT '',
    event_type                    LowCardinality(String) DEFAULT '',
    event_action                  String DEFAULT '',
    event_severity                UInt8 DEFAULT 0,
    event_outcome                 LowCardinality(String) DEFAULT 'unknown',
    event_dataset                 LowCardinality(String) DEFAULT '',
    message                       String DEFAULT '',

    host_name                     String DEFAULT '',
    host_ip                       Array(String),
    observer_vendor               LowCardinality(String) DEFAULT '',
    observer_product              LowCardinality(String) DEFAULT '',

    source_ip                     String DEFAULT '',
    source_port                   UInt16 DEFAULT 0,
    source_geo_country_iso_code   LowCardinality(String) DEFAULT '',
    destination_ip                String DEFAULT '',
    destination_port              UInt16 DEFAULT 0,
    network_protocol              LowCardinality(String) DEFAULT '',
    network_transport             LowCardinality(String) DEFAULT '',
    network_bytes                 UInt64 DEFAULT 0,

    user_name                     String DEFAULT '',
    user_id                       String DEFAULT '',
    user_domain                   String DEFAULT '',
    process_name                  String DEFAULT '',
    process_pid                   UInt32 DEFAULT 0,
    process_command_line          String DEFAULT '',
    process_executable            String DEFAULT '',
    file_path                     String DEFAULT '',
    file_name                     String DEFAULT '',
    file_hash_sha256              String DEFAULT '',

    log_level                     LowCardinality(String) DEFAULT '',
    log_logger                    String DEFAULT '',

    threat_tactic_name            String DEFAULT '',
    threat_technique_id           LowCardinality(String) DEFAULT '',
    threat_technique_name         String DEFAULT '',

    labels                        Map(String, String),
    tags                          Array(String),
    raw                           String CODEC(ZSTD(3)),

    INDEX idx_source_ip source_ip TYPE bloom_filter GRANULARITY 4,
    INDEX idx_user_name user_name TYPE bloom_filter GRANULARITY 4,
    INDEX idx_technique threat_technique_id TYPE bloom_filter GRANULARITY 4
)
ENGINE = MergeTree
PARTITION BY toDate(`@timestamp`)
ORDER BY (host_name, `@timestamp`)
TTL toDateTime(`@timestamp`) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Dead-letter: events that failed validation. Kept for inspection, never silently dropped.
CREATE TABLE IF NOT EXISTS events_dlq
(
    ts     DateTime64(3, 'UTC') DEFAULT now64(3),
    raw    String CODEC(ZSTD(3)),
    error  String
)
ENGINE = MergeTree
PARTITION BY toDate(ts)
ORDER BY ts
TTL toDateTime(ts) + INTERVAL 14 DAY;
