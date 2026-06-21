"""Outbound alerts via Resend email (primary) and optional Slack webhook.

All functions are best-effort and no-op silently when the relevant integration
is not configured, so the scan pipeline never fails because of alerting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from app.config import settings
from app.services.report import render_email_html, render_whatsapp_text

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


def send_whatsapp(to: str, body: str) -> bool:
    """Send a WhatsApp message via Twilio. No-op when not configured."""
    if not (settings.twilio_account_sid and settings.twilio_auth_token and to):
        return False
    to_fmt = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    try:
        resp = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
            data={"From": settings.twilio_whatsapp_from, "To": to_fmt, "Body": body},
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=15,
        )
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


def send_document_alert(email: str, filename: str, result: dict) -> bool:
    """Email the owner when an uploaded document fails its GDPR compliance check."""
    if not email:
        return False
    failed = [c for c in result.get("checks", []) if not c["passed"]]
    rows = "".join(
        '<div style="border:1px solid #eee;border-radius:8px;padding:10px;margin:6px 0;">'
        f'<strong>{c["requirement"]}</strong>'
        f'<br><span style="color:#999;font-size:12px;">{c["article"]}</span></div>'
        for c in failed
    ) or "<p>All key clauses present.</p>"
    score = result.get("score", "")
    docs_url = f"{settings.public_app_url}/documents"
    html = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:auto;">
  <div style="background:#0a0613;padding:20px;border-radius:10px 10px 0 0;">
    <span style="color:#fff;font-size:22px;font-weight:bold;">GUARDA</span>
    <div style="color:#a78bfa;font-size:13px;">Compliance monitoring</div>
  </div>
  <div style="padding:20px;border:1px solid #eee;border-top:none;border-radius:0 0 10px 10px;">
    <h2 style="margin:0 0 6px;">GDPR gaps in “{filename}”</h2>
    <p style="color:#333;">Compliance coverage: <strong>{score}/100</strong>.
    {result.get('summary', '')}</p>
    <h3 style="margin:16px 0 6px;color:#7c5cff;">Clauses to add</h3>
    {rows}
    <a href="{docs_url}" style="display:inline-block;margin-top:16px;background:#7c5cff;
      color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;">Review documents</a>
  </div>
</div>"""
    subject = f"[Guarda] GDPR gaps found in {filename}"
    sent = send_email(email, subject, html)
    send_slack(f":page_facing_up: Guarda found GDPR gaps in *{filename}* ({score}/100).")
    return sent


def send_sensitive_alert(
    asset: str,
    flagged: list[Finding],
    report: dict,
    scan_id: str,
    *,
    email: str | None = None,
    whatsapp: str | None = None,
) -> bool:
    """Alert the owner (email + WhatsApp) when sensitive findings are discovered."""
    report_url = f"{settings.public_app_url}/reports/{scan_id}"
    subject = f"[Guarda] {len(flagged)} sensitive finding(s) on {asset}"
    sent = False
    if email:
        html = render_email_html(report, report_url)
        sent = send_email(email, subject, html) or sent
    if whatsapp:
        text = render_whatsapp_text(report, report_url)
        send_whatsapp(whatsapp, text)
    send_slack(
        f":rotating_light: Guarda found {len(flagged)} sensitive finding(s) on *{asset}*."
    )
    return sent
