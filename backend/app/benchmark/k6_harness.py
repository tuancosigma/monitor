"""k6 performance harness: run a scenario, parse its JSON summary, store the result.

Parser is pure + unit-tested. Targets validate the P1 non-functional goals:
ingest ≥ 10k events/s, query latency p95 < 2000ms. No fabricated numbers — values come
straight from the k6 summary produced against the live compose stack.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark_run import BenchmarkRun

K6_DIR = Path(__file__).resolve().parents[3] / "k6"

INGEST_TARGET_EVENTS_S = 10_000.0
QUERY_LATENCY_TARGET_MS = 2_000.0


def parse_k6_summary(scenario: str, summary: dict[str, Any]) -> tuple[float, str, bool]:
    """Extract (metric_value, unit, passed) from a k6 end-of-test summary JSON."""
    metrics = summary.get("metrics", {})
    if scenario == "ingest_throughput":
        rate = float(metrics.get("iterations", {}).get("rate", 0.0))
        return round(rate, 1), "events/s", rate >= INGEST_TARGET_EVENTS_S
    if scenario == "query_latency":
        p95 = float(metrics.get("http_req_duration", {}).get("values", {}).get("p(95)", 0.0))
        return round(p95, 1), "ms_p95", 0.0 < p95 < QUERY_LATENCY_TARGET_MS
    raise ValueError(f"unknown scenario '{scenario}'")


def k6_available() -> bool:
    return shutil.which("k6") is not None


async def run_k6(db: AsyncSession, scenario: str) -> BenchmarkRun:
    """Run a k6 scenario against the live stack and persist the measured result."""
    if not k6_available():
        raise RuntimeError("k6 not installed")
    script = K6_DIR / f"{scenario}.js"
    if not script.exists():
        raise ValueError(f"no k6 script for scenario '{scenario}'")

    proc = await asyncio.create_subprocess_exec(
        "k6", "run", "--summary-export", "/dev/stdout", str(script),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    summary = json.loads(stdout or b"{}")
    value, unit, passed = parse_k6_summary(scenario, summary)

    run = BenchmarkRun(
        scenario=scenario, metric_value=value, metric_unit=unit, passed=passed,
        raw_summary=summary.get("metrics", {}),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run
