"""
agent.py
Main 24/7 polling loop.
- Runs all alert rules every POLL_INTERVAL_SECONDS
- Deduplicates alerts using an in-memory cooldown map
- Sends a single batched email per poll cycle if any rules triggered
"""
import time
import logging
from datetime import datetime
from typing import Dict

from config import POLL_INTERVAL_SECONDS, ALERT_COOLDOWN_SECONDS, ENV
from alert_rules import ALL_RULES, AlertResult
from email_sender import send_alert_email

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("monitoring-agent")

# ── Cooldown tracker  {rule_name: last_alerted_timestamp} ────────────────────
_last_alerted: Dict[str, float] = {}


def _is_in_cooldown(rule_name: str) -> bool:
    last = _last_alerted.get(rule_name, 0)
    return (time.time() - last) < ALERT_COOLDOWN_SECONDS


def _mark_alerted(rule_name: str):
    _last_alerted[rule_name] = time.time()


def run_once():
    """Execute one full poll cycle."""
    log.info(f"--- Poll cycle started [{ENV.upper()}] ---")
    triggered_alerts = []

    for rule_fn in ALL_RULES:
        try:
            result: AlertResult = rule_fn()
            if result.triggered:
                if _is_in_cooldown(result.rule_name):
                    log.info(f"[COOLDOWN] {result.rule_name} — skipping (already alerted recently)")
                else:
                    log.warning(f"[ALERT] {result.message}")
                    triggered_alerts.append(result)
                    _mark_alerted(result.rule_name)
            else:
                log.info(f"[OK] {result.rule_name} — {result.message}")
        except Exception as e:
            log.error(f"[ERROR] Rule {rule_fn.__name__} raised: {e}")

    if triggered_alerts:
        log.warning(f"Sending alert email for {len(triggered_alerts)} triggered rule(s)...")
        send_alert_email(triggered_alerts)
    else:
        log.info("All checks passed — no alerts.")

    log.info("--- Poll cycle complete ---\n")


def main():
    log.info(f"🚀 School Management Monitoring Agent started")
    log.info(f"   Environment  : {ENV.upper()}")
    log.info(f"   Poll interval: {POLL_INTERVAL_SECONDS}s")
    log.info(f"   Alert cooldown: {ALERT_COOLDOWN_SECONDS}s")

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            log.info("Agent stopped by user.")
            break
        except Exception as e:
            log.error(f"Unexpected error in main loop: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
