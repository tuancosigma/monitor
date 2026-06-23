"""Trivy (container/image CVE) parsing → findings + CIS-style score.

The parser is pure and unit-tested against sample Trivy JSON; the runner shells out to
``trivy`` only when present (it is not available on a Windows host — run via compose).
"""

from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any

# Severity penalties subtracted from a 100 baseline (capped at 0).
_PENALTY = {"CRITICAL": 15.0, "HIGH": 7.0, "MEDIUM": 2.0, "LOW": 0.5, "UNKNOWN": 0.5}


def parse_trivy_json(data: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    """Return (findings, score 0..100) from Trivy JSON output."""
    findings: list[dict[str, Any]] = []
    penalty = 0.0
    for result in data.get("Results", []) or []:
        for vuln in result.get("Vulnerabilities", []) or []:
            severity = str(vuln.get("Severity", "UNKNOWN")).upper()
            penalty += _PENALTY.get(severity, 0.5)
            findings.append(
                {
                    "id": vuln.get("VulnerabilityID"),
                    "severity": severity,
                    "package": vuln.get("PkgName"),
                    "title": vuln.get("Title") or vuln.get("Description", "")[:120],
                }
            )
    score = max(0.0, 100.0 - penalty)
    return findings, round(score, 1)


def trivy_available() -> bool:
    return shutil.which("trivy") is not None


async def run_trivy(target: str) -> tuple[list[dict[str, Any]], float]:
    """Run ``trivy image --format json <target>`` and parse it. Raises if trivy absent."""
    if not trivy_available():
        raise RuntimeError("trivy not installed (run inside the Linux container)")
    proc = await asyncio.create_subprocess_exec(
        "trivy", "image", "--quiet", "--format", "json", target,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return parse_trivy_json(json.loads(stdout or b"{}"))
