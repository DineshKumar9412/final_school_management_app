"""
alert_rules.py
Defines every metric query + threshold check.
Each rule returns an AlertResult (triggered=True/False, value, message).
"""
from dataclasses import dataclass, field
from typing import Optional
import requests
from config import PROMETHEUS_URL, THRESHOLDS, ENV


@dataclass
class AlertResult:
    rule_name:  str
    triggered:  bool
    value:      Optional[float]
    threshold:  Optional[float]
    message:    str
    severity:   str = "WARNING"   # WARNING | CRITICAL


def _query(promql: str) -> Optional[float]:
    """Run an instant PromQL query, return the first scalar value or None."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1])
    except Exception as e:
        print(f"[PromQL ERROR] {promql!r} → {e}")
    return None


def check_app_up() -> AlertResult:
    """Check if the FastAPI app is reachable via Prometheus scrape."""
    job = "school-app-prod" if ENV == "prod" else "school-app-preprod"
    val = _query(f'up{{job="fastapi"}}')
    if val is None or val == 0:
        return AlertResult(
            rule_name="app_down",
            triggered=True,
            value=val,
            threshold=1,
            message=f"🔴 [{ENV.upper()}] School App is DOWN! Prometheus cannot scrape it.",
            severity="CRITICAL",
        )
    return AlertResult("app_down", False, val, 1, "App is up.", "CRITICAL")


def check_cpu() -> AlertResult:
    thresh = THRESHOLDS["cpu_usage_percent"]
    val = _query(
        '100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'
    )
    triggered = val is not None and val > thresh
    return AlertResult(
        rule_name="cpu_usage_percent",
        triggered=triggered,
        value=val,
        threshold=thresh,
        message=(
            f"🔴 [{ENV.upper()}] High CPU: {val:.1f}% (threshold {thresh}%)"
            if triggered else "CPU OK"
        ),
        severity="CRITICAL" if val and val > 95 else "WARNING",
    )


def check_memory() -> AlertResult:
    thresh = THRESHOLDS["memory_usage_percent"]
    val = _query(
        "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))"
    )
    triggered = val is not None and val > thresh
    return AlertResult(
        rule_name="memory_usage_percent",
        triggered=triggered,
        value=val,
        threshold=thresh,
        message=(
            f"🟠 [{ENV.upper()}] High Memory: {val:.1f}% (threshold {thresh}%)"
            if triggered else "Memory OK"
        ),
        severity="CRITICAL" if val and val > 95 else "WARNING",
    )


def check_disk() -> AlertResult:
    thresh = THRESHOLDS["disk_usage_percent"]
    val = _query(
        '100 * (1 - (node_filesystem_avail_bytes{fstype!="tmpfs",mountpoint="/"}'
        " / node_filesystem_size_bytes{fstype!=\"tmpfs\",mountpoint=\"/\"}))"
    )
    triggered = val is not None and val > thresh
    return AlertResult(
        rule_name="disk_usage_percent",
        triggered=triggered,
        value=val,
        threshold=thresh,
        message=(
            f"🟠 [{ENV.upper()}] High Disk Usage: {val:.1f}% (threshold {thresh}%)"
            if triggered else "Disk OK"
        ),
        severity="CRITICAL" if val and val > 95 else "WARNING",
    )


def check_http_error_rate() -> AlertResult:
    thresh = THRESHOLDS["http_error_rate_percent"]
    val = _query(
        "100 * sum(rate(http_requests_total{status=~'5..'}[5m]))"
        " / sum(rate(http_requests_total[5m]))"
    )
    triggered = val is not None and val > thresh
    return AlertResult(
        rule_name="http_error_rate_percent",
        triggered=triggered,
        value=val,
        threshold=thresh,
        message=(
            f"🔴 [{ENV.upper()}] High HTTP Error Rate: {val:.2f}% (threshold {thresh}%)"
            if triggered else "HTTP error rate OK"
        ),
        severity="CRITICAL",
    )


def check_latency_p95() -> AlertResult:
    thresh = THRESHOLDS["http_p95_latency_seconds"]
    val = _query(
        "histogram_quantile(0.95, sum(rate("
        "http_request_duration_seconds_bucket[5m])) by (le))"
    )
    triggered = val is not None and val > thresh
    return AlertResult(
        rule_name="http_p95_latency_seconds",
        triggered=triggered,
        value=val,
        threshold=thresh,
        message=(
            f"🟡 [{ENV.upper()}] Slow Responses: P95 latency {val:.3f}s (threshold {thresh}s)"
            if triggered else "Latency OK"
        ),
        severity="WARNING",
    )


ALL_RULES = [
    check_app_up,
    check_cpu,
    check_memory,
    check_disk,
    check_http_error_rate,
    check_latency_p95,
]
