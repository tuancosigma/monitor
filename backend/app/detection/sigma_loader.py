"""Sigma rule loader and parser.

Parses YAML-based Sigma rules, extracts search selections, conditions, temporal thresholds,
and maps tags to MITRE ATT&CK tactics/techniques.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.core.logging import get_logger

log = get_logger("sentinel.sigma_loader")

# A mapping of common technique prefixes or tags to MITRE names/tactics
MITRE_TACTICS_MAP = {
    "t1110": {"tactic": "Credential Access", "name": "Brute Force"},
    "t1078": {
        "tactic": "Defense Evasion / Persistence / Privilege Escalation / Initial Access",
        "name": "Valid Accounts",
    },
    "t1136": {"tactic": "Persistence", "name": "Create Account"},
    "t1021": {"tactic": "Lateral Movement", "name": "Remote Services"},
    "t1059": {"tactic": "Execution", "name": "Command and Scripting Interpreter"},
    "t1562": {"tactic": "Defense Evasion", "name": "Impair Defenses"},
    "t1003": {"tactic": "Credential Access", "name": "OS Credential Dumping"},
    "t1046": {"tactic": "Discovery", "name": "Network Service Scanning"},
}


class SigmaDetection(BaseModel):
    """Detection block in a Sigma rule."""

    selections: dict[str, Any] = Field(default_factory=dict)
    condition: str
    timeframe: str | None = None  # e.g., "1m", "5m", "1h"
    count: dict[str, Any] | None = None  # e.g., {"field": "source_ip", "op": "gte", "value": 5}


class SigmaRule(BaseModel):
    """Parsed representation of a Sigma rule."""

    id: str
    title: str
    description: str | None = None
    status: str | None = None
    severity: str  # info, low, medium, high, critical
    tags: list[str] = Field(default_factory=list)
    detection: SigmaDetection

    def get_mitre_mappings(self) -> list[dict[str, Any]]:
        """Extract MITRE ATT&CK tactic/technique details from tags."""
        mappings = []
        for tag in self.tags:
            tag_lower = tag.lower()
            if tag_lower.startswith("attack.t"):
                technique_id = tag_lower.split(".")[-1].upper()
                info = MITRE_TACTICS_MAP.get(technique_id.lower(), {})
                mappings.append({
                    "tactic": info.get("tactic", "Unknown Tactic"),
                    "technique_id": technique_id,
                    "technique_name": info.get("name", "Unknown Technique"),
                })
        return mappings


def parse_sigma_rule(content: str) -> SigmaRule:
    """Parse raw YAML content into a SigmaRule model."""
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("Invalid Sigma rule format: must be a YAML dictionary")

    # Required metadata fields
    rule_id = data.get("id")
    title = data.get("title")
    severity = data.get("severity")
    detection_raw = data.get("detection")

    if not rule_id or not title or not severity or not detection_raw:
        raise ValueError("Missing required fields (id, title, severity, detection)")

    # Parse detection block
    detection_dict = dict(detection_raw)
    condition = detection_dict.pop("condition", None)
    timeframe = detection_dict.pop("timeframe", None)
    count = detection_dict.pop("count", None)

    if not condition:
        raise ValueError("Detection block is missing condition field")

    # The rest are selections
    selections = detection_dict

    detection = SigmaDetection(
        selections=selections,
        condition=str(condition),
        timeframe=timeframe,
        count=count,
    )

    return SigmaRule(
        id=str(rule_id),
        title=str(title),
        description=data.get("description"),
        status=data.get("status"),
        severity=str(severity).lower(),
        tags=data.get("tags", []),
        detection=detection,
    )


def load_rules_from_dir(directory_path: str) -> list[SigmaRule]:
    """Load and parse all Sigma rule files in a directory."""
    rules: list[SigmaRule] = []
    dir_path = Path(directory_path)
    if not dir_path.exists():
        log.warning("rules_directory_missing", path=str(dir_path))
        return rules

    for file_path in dir_path.glob("**/*.yml"):
        try:
            content = file_path.read_text(encoding="utf-8")
            rule = parse_sigma_rule(content)
            rules.append(rule)
        except Exception as exc:
            log.error("failed_to_load_rule", file=file_path.name, error=str(exc))

    log.info("sigma_rules_loaded", count=len(rules), path=str(dir_path))
    return rules
