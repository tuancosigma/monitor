# ECS-lite — unified event schema (condensed from Elastic Common Schema)

Every log/metric/alert is normalized to this structure before being written to ClickHouse.
Missing fields are left null. Consumed by the Phase 1 ingest pipeline.

## Core
- @timestamp           : datetime (UTC, ISO8601)  — required
- event.kind           : enum [event, alert, metric, state, signal]
- event.category       : enum [authentication, network, process, file, malware, intrusion_detection, web, host, configuration]
- event.type           : enum [start, end, info, error, connection, access, change, denied, allowed]
- event.action         : string (e.g. "ssh_login_failed")
- event.severity       : int 0..100  (0=info … 100=critical)
- event.outcome        : enum [success, failure, unknown]
- event.dataset        : string (source, e.g. "linux.auth")
- message              : string (human-readable description)

## Host / observer
- host.name, host.ip[], host.os.name, host.os.version
- observer.vendor, observer.product   (e.g. Wazuh, Prometheus, Sentinel)

## Network
- source.ip, source.port, source.geo.country_iso_code
- destination.ip, destination.port
- network.protocol, network.transport, network.bytes

## Identity / process / file
- user.name, user.id, user.domain
- process.name, process.pid, process.command_line, process.executable
- file.path, file.name, file.hash.sha256

## Log
- log.level, log.logger

## Threat (MITRE ATT&CK mapping)
- threat.tactic.name
- threat.technique.id      (e.g. "T1110")
- threat.technique.name

## Extensions
- labels        : map(string,string)   — free-form labels
- tags          : array(string)
- raw           : string (original JSON, for traceability)

## ClickHouse `events` table guidance
- Partition by toDate(@timestamp), ORDER BY (host.name, @timestamp)
- TTL on @timestamp (e.g. keep 30 days) for auto-cleanup
- `raw` column ZSTD-compressed; skip indexes for source.ip, user.name, threat.technique.id
