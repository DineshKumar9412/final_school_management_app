"""
email_sender.py
Sends HTML alert emails via SMTP (Gmail or any SMTP provider).
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_FROM, ALERT_TO, ENV
from alert_rules import AlertResult


def _build_html(alerts: List[AlertResult]) -> str:
    rows = ""
    for a in alerts:
        color = "#ff4444" if a.severity == "CRITICAL" else "#ff9800"
        value_str = f"{a.value:.2f}" if a.value is not None else "N/A"
        rows += f"""
        <tr>
          <td style="padding:8px;border:1px solid #ddd;color:{color};font-weight:bold">{a.severity}</td>
          <td style="padding:8px;border:1px solid #ddd">{a.rule_name}</td>
          <td style="padding:8px;border:1px solid #ddd">{value_str}</td>
          <td style="padding:8px;border:1px solid #ddd">{a.threshold}</td>
          <td style="padding:8px;border:1px solid #ddd">{a.message}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
      <h2 style="color:#cc0000">🚨 School Management System — Monitoring Alert</h2>
      <p><strong>Environment:</strong> {ENV.upper()}<br>
         <strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

      <table style="border-collapse:collapse;width:100%">
        <thead>
          <tr style="background:#f44336;color:#fff">
            <th style="padding:10px;border:1px solid #ddd">Severity</th>
            <th style="padding:10px;border:1px solid #ddd">Metric</th>
            <th style="padding:10px;border:1px solid #ddd">Current Value</th>
            <th style="padding:10px;border:1px solid #ddd">Threshold</th>
            <th style="padding:10px;border:1px solid #ddd">Details</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>

      <p style="margin-top:20px;color:#666;font-size:12px">
        This is an automated alert from the School Management Monitoring Agent.<br>
        Please investigate immediately if severity is CRITICAL.
      </p>
    </body></html>"""


def send_alert_email(alerts: List[AlertResult]) -> bool:
    """Send an HTML email for all triggered alerts. Returns True on success."""
    if not alerts:
        return False
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] SMTP_USER / SMTP_PASSWORD not configured — skipping email.")
        return False

    subject = (
        f"🚨 [{ENV.upper()}] CRITICAL Alert — School App"
        if any(a.severity == "CRITICAL" for a in alerts)
        else f"⚠️ [{ENV.upper()}] WARNING Alert — School App"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = ALERT_FROM
    msg["To"]      = ", ".join(ALERT_TO)
    msg.attach(MIMEText(_build_html(alerts), "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(ALERT_FROM, ALERT_TO, msg.as_string())
        print(f"[EMAIL] Alert email sent to {ALERT_TO}  subject='{subject}'")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {e}")
        return False
