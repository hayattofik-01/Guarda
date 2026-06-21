"""AI remediation "advice" for a completed check.

Guarda always computes a deterministic advice summary immediately so a report
is never empty. When a Devin API key is configured, it also dispatches a Devin
session that authors tailored guidance; the next time the scan is refreshed
(on a cron tick or when the report is fetched) the advice is upgraded to the
Devin-authored version.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.models import Finding, Scan

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


def enabled() -> bool:
    return bool(settings.devin_api_key)


def _category_label(category) -> str:
    value = getattr(category, "value", category) or "exposed_data"
    return {
        "sensitive_info": "Sensitive data / secrets",
        "exposed_data": "Exposed files & services",
        "reputation_risk": "Reputation / takeover risk",
        "footprint": "Attack surface",
    }.get(value, value)


def deterministic_advice(target_address: str, findings: list[Finding]) -> str:
    """A useful, source-grounded remediation summary built without any LLM."""
    actionable = [
        f
        for f in findings
        if getattr(f.category, "value", f.category) != "footprint"
    ]
    lines: list[str] = []
    if not actionable:
        lines.append(
            f"No exposed data or sensitive findings were detected for "
            f"**{target_address}** in this run. Keep monitoring on schedule — "
            "new subdomains and services appear over time."
        )
        return "\n".join(lines)

    # Group by category, surface the highest-priority items first.
    by_cat: dict[str, list[Finding]] = {}
    for f in actionable:
        by_cat.setdefault(_category_label(f.category), []).append(f)

    lines.append(
        f"Guarda found {len(actionable)} issue(s) worth acting on for "
        f"**{target_address}**. Prioritised remediation:"
    )
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    for label, items in by_cat.items():
        items.sort(key=lambda f: order.get(getattr(f.severity, "value", "info"), 5))
        lines.append(f"\n### {label}")
        for f in items[:5]:
            sev = getattr(f.severity, "value", "info").upper()
            tip = f.remediation or "Restrict public access and remove the exposure."
            where = f" (`{f.location}`)" if f.location else ""
            lines.append(f"- **[{sev}] {f.title}**{where} — {tip}")
        if len(items) > 5:
            lines.append(f"- …and {len(items) - 5} more in this category.")
    return "\n".join(lines)


def _build_prompt(target_address: str, findings: list[Finding], gdpr_summary: str | None) -> str:
    bullet = []
    for f in findings:
        if getattr(f.category, "value", f.category) == "footprint":
            continue
        sev = getattr(f.severity, "value", "info")
        bullet.append(f"- [{sev}] {f.title} @ {f.location or f.host or target_address}")
    findings_block = "\n".join(bullet[:40]) or "- (no actionable exposures)"
    gdpr_block = gdpr_summary or "(no GDPR summary available)"
    return (
        "You are a senior security & GDPR advisor for a SaaS founder. "
        f"Their external attack surface for {target_address} was scanned. "
        "Write concise, prioritised, non-technical remediation advice (markdown, "
        "max ~250 words) they can act on this week. Reference the specific "
        "findings and GDPR gaps. Do not invent findings.\n\n"
        f"External findings:\n{findings_block}\n\n"
        f"GDPR assessment:\n{gdpr_block}\n\n"
        "When finished, set your structured output to a JSON object "
        '{"advice_markdown": "<your markdown advice>"}.'
    )


def start_advice(
    scan: Scan,
    target_address: str,
    findings: list[Finding],
    gdpr_summary: str | None,
) -> None:
    """Populate deterministic advice now; dispatch Devin if configured.

    Mutates ``scan`` in place (caller commits).
    """
    scan.advice = deterministic_advice(target_address, findings)
    scan.advice_source = "automated"
    scan.advice_status = "ready"

    if not enabled():
        return
    try:
        resp = httpx.post(
            f"{settings.devin_api_base}/sessions",
            headers={"Authorization": f"Bearer {settings.devin_api_key}"},
            json={"prompt": _build_prompt(target_address, findings, gdpr_summary)},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        session_id = data.get("session_id")
        if session_id:
            scan.devin_session_id = session_id
            scan.advice_status = "pending"  # deterministic shown until Devin replies
    except Exception as exc:  # noqa: BLE001 - advice is best-effort
        logger.warning("Devin advice dispatch failed: %s", exc)


def refresh_advice(scan: Scan) -> bool:
    """If a Devin advice session is pending, pull its result. Returns True if updated.

    Mutates ``scan`` in place (caller commits).
    """
    if scan.advice_status != "pending" or not scan.devin_session_id or not enabled():
        return False
    try:
        resp = httpx.get(
            f"{settings.devin_api_base}/session/{scan.devin_session_id}",
            headers={"Authorization": f"Bearer {settings.devin_api_key}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Devin advice poll failed: %s", exc)
        return False

    structured = data.get("structured_output") or {}
    advice_md = None
    if isinstance(structured, dict):
        advice_md = structured.get("advice_markdown") or structured.get("advice")
    status = (data.get("status_enum") or "").lower()

    if advice_md:
        scan.advice = advice_md.strip()
        scan.advice_source = "devin"
        scan.advice_status = "ready"
        return True
    if status in {"stopped", "finished", "expired", "blocked"}:
        # Session ended without structured advice; keep the deterministic version.
        scan.advice_status = "ready"
        return True
    return False
