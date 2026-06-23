"""Sandboxed Jinja template rendering for notifications.

Enforces sandboxing to prevent Server-Side Template Injection (SSTI)
from user-defined notification templates.
"""

from __future__ import annotations

from jinja2.sandbox import SandboxedEnvironment

from app.models.alert import Alert
from app.models.incident import Incident

# Initialize the Sandboxed Environment
env = SandboxedEnvironment()

DEFAULT_ALERT_TEMPLATE = (
    "🔔 [{{ alert.severity | upper }}] Alert: {{ alert.rule_name }}\n"
    "Status: {{ alert.status }}\n"
    "Time: {{ alert.timestamp }}\n"
    "Rule ID: {{ alert.rule_id }}\n"
    "{% if alert.entities -%}\n"
    "Entities:\n"
    "{% for entity in alert.entities -%}\n"
    "  - {{ entity.type }}: {{ entity.value }}\n"
    "{% endfor -%}\n"
    "{% endif -%}\n"
    "{% if alert.mitre_mapping -%}\n"
    "MITRE ATT&CK:\n"
    "{% for mapping in alert.mitre_mapping -%}\n"
    "  - {{ mapping.tactic }} ({{ mapping.technique_id }}): {{ mapping.technique_name }}\n"
    "{% endfor -%}\n"
    "{% endif -%}"
)

DEFAULT_INCIDENT_TEMPLATE = (
    "🚨 [{{ incident.severity | upper }}] Incident: {{ incident.title }}\n"
    "Description: {{ incident.description }}\n"
    "Status: {{ incident.status }}\n"
    "First Seen: {{ incident.first_seen }}\n"
    "Last Seen: {{ incident.last_seen }}\n"
    "{% if incident.entities -%}\n"
    "Entities:\n"
    "{% for entity in incident.entities -%}\n"
    "  - {{ entity.type }}: {{ entity.value }}\n"
    "{% endfor -%}\n"
    "{% endif -%}"
)


def render_alert_notification(alert: Alert, template_str: str | None = None) -> str:
    """Render notification text for an Alert using Sandboxed Jinja2."""
    t_str = template_str or DEFAULT_ALERT_TEMPLATE
    template = env.from_string(t_str)
    # Convert Alert model to dict context for Jinja
    context = {
        "alert": {
            "id": alert.id,
            "rule_id": alert.rule_id,
            "rule_name": alert.rule_name,
            "severity": alert.severity,
            "status": alert.status,
            "timestamp": alert.timestamp.isoformat() if alert.timestamp else "",
            "dedup_key": alert.dedup_key,
            "entities": alert.entities,
            "mitre_mapping": alert.mitre_mapping,
            "assignee": alert.assignee,
        }
    }
    return template.render(context).strip()


def render_incident_notification(incident: Incident, template_str: str | None = None) -> str:
    """Render notification text for an Incident using Sandboxed Jinja2."""
    t_str = template_str or DEFAULT_INCIDENT_TEMPLATE
    template = env.from_string(t_str)
    context = {
        "incident": {
            "id": incident.id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "status": incident.status,
            "first_seen": incident.first_seen.isoformat() if incident.first_seen else "",
            "last_seen": incident.last_seen.isoformat() if incident.last_seen else "",
            "entities": incident.entities,
            "assignee": incident.assignee,
        }
    }
    return template.render(context).strip()
