"""Outbound alerts via Resend email (primary) and optional Slack webhook.

All functions are best-effort and no-op silently when the relevant integration
is not configured, so the scan pipeline never fails because of alerting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from app.config import settings
from app.services.report import render_email_html

if TYPE_CHECKING:
    from app.models import Finding


def send_slack(text: str) -> bool:
    if not settings.slack_webhook_url:
        return False
    try:
        resp = httpx.post(settings.slack_webhook_url, json={"text": text}, timeout=10)
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. No-op when RESEND_API_KEY/recipient is missing."""
    if not settings.resend_api_key or not to:
        return False
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.resend_from_email,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=15,
        )
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


def send_sensitive_alert(
    to: str,
    asset: str,
    flagged: list[Finding],
    report: dict,
    scan_id: str,
) -> bool:
    """Email the asset owner when sensitive/high-risk findings are discovered."""
    report_url = f"{settings.public_app_url}/reports/{scan_id}"
    subject = f"[Guarda] {len(flagged)} sensitive finding(s) on {asset}"
    html = render_email_html(report, report_url)
    sent = send_email(to, subject, html)
    send_slack(
        f":rotating_light: Guarda found {len(flagged)} sensitive finding(s) on *{asset}*."
    )
    return sent
