"""Outbound alerts via Slack webhook and/or SendGrid email.

All functions are best-effort and no-op silently when the relevant integration
is not configured, so the scan pipeline never fails because of alerting.
"""

from __future__ import annotations

import httpx

from app.config import settings


def send_slack(text: str) -> bool:
    if not settings.slack_webhook_url:
        return False
    try:
        resp = httpx.post(settings.slack_webhook_url, json={"text": text}, timeout=10)
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


def send_email(subject: str, body: str, to: str | None = None) -> bool:
    if not settings.sendgrid_api_key or not to:
        return False
    try:
        resp = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": settings.sendgrid_from_email},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
            timeout=10,
        )
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


def send_scan_complete(address: str, finding_count: int) -> None:
    text = f":mag: Perimeter scan complete for *{address}* — {finding_count} finding(s)."
    send_slack(text)
