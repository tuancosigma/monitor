"""Unit tests for posture (Trivy/Lynis) + benchmark (k6) parsers."""

from __future__ import annotations

from app.benchmark.k6_harness import parse_k6_summary
from app.benchmark.lynis import parse_lynis_report
from app.benchmark.trivy import parse_trivy_json


def test_trivy_parse_scores_and_collects_findings() -> None:
    data = {
        "Results": [
            {
                "Vulnerabilities": [
                    {"VulnerabilityID": "CVE-1", "Severity": "CRITICAL", "PkgName": "openssl",
                     "Title": "rce"},
                    {"VulnerabilityID": "CVE-2", "Severity": "LOW", "PkgName": "zlib",
                     "Title": "info leak"},
                ]
            }
        ]
    }
    findings, score = parse_trivy_json(data)
    assert len(findings) == 2
    assert score == round(100.0 - 15.0 - 0.5, 1)  # critical + low penalties
    assert findings[0]["id"] == "CVE-1"


def test_trivy_clean_image_scores_100() -> None:
    findings, score = parse_trivy_json({"Results": []})
    assert findings == []
    assert score == 100.0


def test_lynis_parse_reads_index_and_warnings() -> None:
    report = "\n".join(
        ["hardening_index=68", "warning[]=SSH root login enabled", "suggestion[]=Install fail2ban"]
    )
    findings, score = parse_lynis_report(report)
    assert score == 68.0
    assert any(f["severity"] == "warning" for f in findings)
    assert any(f["severity"] == "suggestion" for f in findings)


def test_k6_ingest_throughput_pass_fail() -> None:
    fast = {"metrics": {"iterations": {"rate": 12000.0}}}
    value, unit, passed = parse_k6_summary("ingest_throughput", fast)
    assert value == 12000.0
    assert unit == "events/s"
    assert passed is True

    slow = {"metrics": {"iterations": {"rate": 5000.0}}}
    _, _, passed_slow = parse_k6_summary("ingest_throughput", slow)
    assert passed_slow is False


def test_k6_query_latency_pass_fail() -> None:
    good = {"metrics": {"http_req_duration": {"values": {"p(95)": 850.0}}}}
    value, unit, passed = parse_k6_summary("query_latency", good)
    assert value == 850.0
    assert unit == "ms_p95"
    assert passed is True

    bad = {"metrics": {"http_req_duration": {"values": {"p(95)": 2500.0}}}}
    _, _, passed_bad = parse_k6_summary("query_latency", bad)
    assert passed_bad is False
