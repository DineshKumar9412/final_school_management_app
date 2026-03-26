import os
from dotenv import load_dotenv

load_dotenv()

# ── Prometheus ────────────────────────────────────────────────────────────────
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_FROM    = os.getenv("ALERT_FROM", SMTP_USER)
ALERT_TO      = os.getenv("ALERT_TO", "").split(",")   # comma-separated recipients

# ── Environment label ─────────────────────────────────────────────────────────
ENV = os.getenv("ENV", "preprod")   # "preprod" | "prod"

# ── Poll interval ─────────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

# ── Alert cooldown (avoid repeated emails for same alert) ─────────────────────
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))  # 5 min

# ── Thresholds ────────────────────────────────────────────────────────────────
THRESHOLDS = {
    "cpu_usage_percent":         float(os.getenv("THRESH_CPU",          "85")),
    "memory_usage_percent":      float(os.getenv("THRESH_MEMORY",       "85")),
    "disk_usage_percent":        float(os.getenv("THRESH_DISK",         "90")),
    "http_error_rate_percent":   float(os.getenv("THRESH_HTTP_ERROR",   "5")),
    "http_p95_latency_seconds":  float(os.getenv("THRESH_LATENCY_P95",  "2.0")),
    "app_down":                  1,   # binary – app is unreachable
}
