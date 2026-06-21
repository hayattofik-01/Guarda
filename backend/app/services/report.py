"""Non-technical report generator.

Turns raw scanner findings into plain-language guidance a non-technical owner
can act on: what we found, why it matters, and what to do — grouped by the
three Guarda categories and ordered by urgency.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.services.gdpr import gdpr_assessment
from app.services.scoring import compliance_checklist, compute_score

if TYPE_CHECKING:
    from app.models import Finding, Scan, Target

# Plain-language metadata per category.
CATEGORY_META = {
    "sensitive_info": {
        "title": "Sensitive Information Found",
        "plain": (
            "Private information (like passwords, API keys, or staff emails) is "
            "visible to anyone on the internet."
        ),
    },
    "exposed_data": {
        "title": "Exposed Data Detected",
        "plain": (
            "Files, folders, or admin pages that should be private are reachable "
            "by the public."
        ),
    },
    "reputation_risk": {
        "title": "Reputation Risk Identified",
        "plain": (
            "Something could let an attacker impersonate your brand or damage how "
            "customers see you."
        ),
    },
    "footprint": {
        "title": "Your Digital Footprint",
        "plain": "The public-facing assets we found that make up your online presence.",
    },
}

# Friendly severity wording.
SEVERITY_LABEL = {
    "critical": "Critical — fix immediately",
    "high": "High — fix soon",
    "medium": "Medium — worth fixing",
    "low": "Low — keep an eye on it",
    "info": "Informational",
}

_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _overall_risk(findings: list[Finding]) -> str:
    if any(f.severity.value in ("critical", "high") for f in findings):
        return "Action needed"
    if any(f.severity.value == "medium" for f in findings):
        return "Some attention needed"
    if findings:
        return "Looking good"
    return "All clear"


def _headline(asset: str, risk: str, sensitive: int, exposed: int) -> str:
    if risk == "All clear":
        return f"Good news — we didn't find anything urgent on {asset}."
    parts = []
    if sensitive:
        parts.append(f"{sensitive} sensitive-information issue(s)")
    if exposed:
        parts.append(f"{exposed} exposed-data issue(s)")
    detail = " and ".join(parts) if parts else "a few items to review"
    return f"We reviewed {asset} and found {detail}. Here's what it means and what to do."


def build_report(target: Target, scan: Scan, findings: list[Finding]) -> dict:
    """Build a structured, non-technical report from a scan's findings."""
    by_category: dict[str, list[Finding]] = defaultdict(list)
    by_severity: dict[str, int] = defaultdict(int)
    for f in findings:
        by_category[f.category.value].append(f)
        by_severity[f.severity.value] += 1

    sections = []
    # Stable, urgency-first category order.
    for cat in ("sensitive_info", "exposed_data", "reputation_risk", "footprint"):
        items = by_category.get(cat, [])
        if not items:
            continue
        items.sort(key=lambda x: _SEVERITY_ORDER.get(x.severity.value, 0), reverse=True)
        meta = CATEGORY_META[cat]
        sections.append(
            {
                "category": cat,
                "title": meta["title"],
                "what_it_means": meta["plain"],
                "count": len(items),
                "items": [
                    {
                        "title": f.title,
                        "severity": f.severity.value,
                        "severity_label": SEVERITY_LABEL.get(f.severity.value, f.severity.value),
                        "where": f.location or f.host or "",
                        "what_happened": f.description or "",
                        "what_to_do": f.remediation or "Review this item with your IT contact.",
                    }
                    for f in items
                ],
            }
        )

    risk = _overall_risk(findings)
    sensitive_count = len(by_category.get("sensitive_info", []))
    exposed_count = len(by_category.get("exposed_data", []))
    score = compute_score(findings)

    return {
        "asset": target.address,
        "label": target.label,
        "generated_at": datetime.now(UTC).isoformat(),
        "scan_id": scan.id,
        "overall_risk": risk,
        "score": score["score"],
        "grade": score["grade"],
        "score_summary": score["summary"],
        "compliance": compliance_checklist(findings),
        "gdpr": gdpr_assessment(target.address, findings, scan_id=scan.id),
        "headline": _headline(target.address, risk, sensitive_count, exposed_count),
        "totals": {
            "findings": len(findings),
            "by_severity": dict(by_severity),
            "sensitive_information": sensitive_count,
            "exposed_data": exposed_count,
            "reputation_risk": len(by_category.get("reputation_risk", [])),
            "footprint": len(by_category.get("footprint", [])),
        },
        "next_steps": _next_steps(risk, sensitive_count, exposed_count),
        "sections": sections,
    }


def _next_steps(risk: str, sensitive: int, exposed: int) -> list[str]:
    steps: list[str] = []
    if sensitive:
        steps.append(
            "Rotate any leaked passwords/API keys right away and turn on "
            "two-factor authentication."
        )
    if exposed:
        steps.append(
            "Lock down the exposed files and admin pages so only your team can "
            "reach them."
        )
    if risk == "All clear":
        steps.append("Keep monitoring on schedule — new risks appear over time.")
    else:
        steps.append("Re-run a scan after fixing to confirm the issues are resolved.")
    return steps


def render_email_html(report: dict, report_url: str) -> str:
    """Render a compact, friendly HTML email from a report dict."""
    rows = []
    for section in report["sections"]:
        if section["category"] == "footprint":
            continue
        rows.append(
            f'<h3 style="margin:18px 0 6px;color:#7c5cff;">{section["title"]} '
            f'({section["count"]})</h3>'
            f'<p style="margin:0 0 8px;color:#555;">{section["what_it_means"]}</p>'
        )
        for item in section["items"][:5]:
            rows.append(
                '<div style="border:1px solid #eee;border-radius:8px;padding:10px;'
                'margin:6px 0;">'
                f'<strong>{item["title"]}</strong><br>'
                f'<span style="color:#999;font-size:12px;">{item["severity_label"]}'
                f' · {item["where"]}</span><br>'
                f'<span style="font-size:13px;">What to do: {item["what_to_do"]}</span>'
                "</div>"
            )
    body = "".join(rows) or "<p>No sensitive items in this scan.</p>"
    grade = report.get("grade", "?")
    score = report.get("score", "")
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:auto;">
  <div style="background:#0a0613;padding:20px;border-radius:10px 10px 0 0;">
    <span style="color:#fff;font-size:22px;font-weight:bold;">GUARDA</span>
    <div style="color:#a78bfa;font-size:13px;">Know your external security score.</div>
  </div>
  <div style="padding:20px;border:1px solid #eee;border-top:none;border-radius:0 0 10px 10px;">
    <div style="display:inline-block;background:#0a0613;color:#fff;font-weight:bold;
      font-size:26px;padding:10px 18px;border-radius:10px;">Score: {grade}</div>
    <span style="color:#999;font-size:13px;margin-left:10px;">{score}/100</span>
    <h2 style="margin:16px 0 0;">{report["headline"]}</h2>
    <p style="color:#333;">Overall status: <strong>{report["overall_risk"]}</strong></p>
    {body}
    <a href="{report_url}" style="display:inline-block;margin-top:16px;background:#7c5cff;
      color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;">
      View full report</a>
  </div>
</div>"""


def render_whatsapp_text(report: dict, report_url: str) -> str:
    """Render a short WhatsApp alert message from a report dict."""
    flagged = [
        item
        for section in report["sections"]
        if section["category"] in ("sensitive_info", "reputation_risk")
        for item in section["items"]
    ]
    lines = [
        f"*Guarda alert* — {report['asset']}",
        f"Security score: {report.get('grade', '?')} ({report.get('score', '')}/100)",
        f"Status: {report['overall_risk']}",
    ]
    if flagged:
        lines.append(f"Top issue: {flagged[0]['title']}")
    lines.append(f"Full report: {report_url}")
    return "\n".join(lines)
