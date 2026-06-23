"""Unit tests for the Sigma rule loader and MITRE mapping extraction."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.detection.sigma_loader import load_rules_from_dir, parse_sigma_rule

SAMPLE_RULE = """
id: 5a8a478b-302a-4db5-b82b-8a8b13c7dbba
title: SSH Brute Force
description: Detects multiple failed SSH authentication attempts from a single source IP.
severity: high
status: experimental
tags:
  - attack.t1110
  - attack.credential_access
detection:
  selection:
    event_category: authentication
    event_outcome: failure
  condition: selection
  timeframe: 1m
  count:
    field: source_ip
    op: gte
    value: 5
"""


def test_parse_valid_sigma_rule() -> None:
    rule = parse_sigma_rule(SAMPLE_RULE)
    assert rule.id == "5a8a478b-302a-4db5-b82b-8a8b13c7dbba"
    assert rule.title == "SSH Brute Force"
    assert rule.severity == "high"
    assert rule.status == "experimental"
    assert rule.detection.condition == "selection"
    assert rule.detection.timeframe == "1m"
    assert rule.detection.count == {"field": "source_ip", "op": "gte", "value": 5}
    assert "selection" in rule.detection.selections
    assert rule.detection.selections["selection"] == {
        "event_category": "authentication",
        "event_outcome": "failure",
    }


def test_mitre_mapping_extraction() -> None:
    rule = parse_sigma_rule(SAMPLE_RULE)
    mappings = rule.get_mitre_mappings()
    assert len(mappings) == 1
    assert mappings[0]["technique_id"] == "T1110"
    assert mappings[0]["tactic"] == "Credential Access"
    assert mappings[0]["technique_name"] == "Brute Force"


def test_load_rules_from_directory() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        rule_file = tmp_path / "test_rule.yml"
        rule_file.write_text(SAMPLE_RULE, encoding="utf-8")

        # Also write an invalid file to verify tolerance
        bad_file = tmp_path / "bad_rule.yml"
        bad_file.write_text("invalid yaml here", encoding="utf-8")

        rules = load_rules_from_dir(tmpdir)
        assert len(rules) == 1
        assert rules[0].title == "SSH Brute Force"
