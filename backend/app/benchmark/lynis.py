"""Lynis (host hardening) parsing → warnings/suggestions + hardening index score.

Pure parser unit-tested against a sample Lynis report; the runner shells out to ``lynis``
only when present (run via the Linux container, not the Windows host).
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any


def parse_lynis_report(report_text: str) -> tuple[list[dict[str, Any]], float]:
    """Parse a Lynis ``lynis-report.dat``. Returns (findings, hardening_index 0..100)."""
    findings: list[dict[str, Any]] = []
    score = 0.0
    for line in report_text.splitlines():
        line = line.strip()
        if line.startswith("hardening_index="):
            try:
                score = float(line.split("=", 1)[1])
            except ValueError:
                score = 0.0
        elif line.startswith("warning[]="):
            findings.append({"severity": "warning", "detail": line.split("=", 1)[1]})
        elif line.startswith("suggestion[]="):
            findings.append({"severity": "suggestion", "detail": line.split("=", 1)[1]})
    return findings, score


def lynis_available() -> bool:
    return shutil.which("lynis") is not None


async def run_lynis() -> tuple[list[dict[str, Any]], float]:
    """Run ``lynis audit system`` and parse the report. Raises if lynis absent."""
    if not lynis_available():
        raise RuntimeError("lynis not installed (run inside the Linux container)")
    proc = await asyncio.create_subprocess_exec(
        "lynis", "audit", "system", "--quiet", "--no-colors",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    try:
        text = await asyncio.to_thread(
            Path("/var/log/lynis-report.dat").read_text, encoding="utf-8"
        )
    except OSError as exc:
        raise RuntimeError(f"lynis report unreadable: {exc}") from exc
    return parse_lynis_report(text)
