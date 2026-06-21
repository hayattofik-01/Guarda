"""GDPR compliance assessment for a scan's external exposures.

A SaaS founder selling to enterprise gets asked "are you GDPR compliant?" on
every security questionnaire. This turns Guarda's external findings into a
plain-English, per-article GDPR posture.

The assessment is produced by **Cala.ai** (queried over its MCP API) when a key
is configured — Cala acts as the structured legal/regulatory reasoning layer.
If Cala is unavailable or returns something unusable, we fall back to a
deterministic heuristic so a report is never blank.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from app.services.cala import CalaClient, CalaError

if TYPE_CHECKING:
    from app.models import Finding

logger = logging.getLogger(__name__)

# Cache one assessment per scan so repeated report views don't re-call Cala.
_CACHE: dict[str, dict] = {}


def _val(x) -> str:
    return x.value if hasattr(x, "value") else (x or "")


def _text(f) -> str:
    return f"{getattr(f, 'title', '') or ''} {getattr(f, 'location', '') or ''}".lower()


def _buckets(findings: list[Finding]) -> dict[str, list]:
    """Group actionable findings into the buckets that map to GDPR obligations."""
    actionable = [f for f in findings if _val(f.category) != "footprint"]
    secret_kw = ("secret", "key", "token", "password", "credential")
    return {
        "actionable": actionable,
        "leaked_secrets": [
            f for f in actionable
            if _val(getattr(f, "source", "")) == "gitleaks"
            or (_val(f.category) == "sensitive_info" and any(k in _text(f) for k in secret_kw))
        ],
        "exposed": [f for f in actionable if _val(f.category) == "exposed_data"],
        "leaked_emails": [
            f for f in actionable
            if _val(getattr(f, "source", "")) == "theharvester"
            and _val(f.category) == "sensitive_info"
        ],
        "sensitive": [f for f in actionable if _val(f.category) == "sensitive_info"],
        "high_risk": [f for f in actionable if _val(f.severity) in ("critical", "high")],
    }


def heuristic_assessment(findings: list[Finding]) -> dict:
    """Deterministic GDPR posture derived directly from findings (no Cala)."""
    b = _buckets(findings)

    def check(article: str, requirement: str, offenders: list, clear: str) -> dict:
        passed = len(offenders) == 0
        detail = clear if passed else f"{len(offenders)} issue(s) found — see the findings below."
        return {
            "article": article,
            "requirement": requirement,
            "passed": passed,
            "detail": detail,
        }

    personal_data = b["sensitive"] + b["exposed"]
    checks = [
        check(
            "Art. 5(1)(f) · 32",
            "Personal data is protected from unauthorised public access",
            personal_data,
            "No personal data found publicly exposed.",
        ),
        check(
            "Art. 32",
            "No credentials are exposed that could compromise personal data",
            b["leaked_secrets"],
            "No leaked credentials detected.",
        ),
        check(
            "Art. 32",
            "Systems processing personal data are not misconfigured or publicly reachable",
            b["exposed"],
            "No misconfigured or publicly exposed assets.",
        ),
        check(
            "Art. 5(1)(c) · 30",
            "Staff and contact personal data is not harvestable in bulk",
            b["leaked_emails"],
            "No bulk-harvestable corporate emails.",
        ),
        check(
            "Art. 33",
            "No active exposure that would trigger a breach notification",
            b["high_risk"],
            "No notifiable breach indicators in your external footprint.",
        ),
    ]
    failed = [c for c in checks if not c["passed"]]
    if not failed:
        summary = (
            "No GDPR red flags in your external footprint. Keep monitoring — "
            "compliance is continuous, not a one-time check."
        )
    else:
        summary = (
            f"{len(failed)} of {len(checks)} GDPR obligations are at risk based on "
            "what's publicly visible. Resolve the items below before an enterprise "
            "data-protection review."
        )
    return {"source": "heuristic", "summary": summary, "checks": checks}


def _findings_brief(findings: list[Finding]) -> str:
    b = _buckets(findings)
    lines = [
        f"- Total actionable exposures: {len(b['actionable'])}",
        f"- Leaked secrets/credentials: {len(b['leaked_secrets'])}",
        f"- Exposed files/admin panels: {len(b['exposed'])}",
        f"- Harvestable staff emails: {len(b['leaked_emails'])}",
        f"- Critical/high severity: {len(b['high_risk'])}",
    ]
    samples = [
        f"  * [{_val(f.severity)}/{_val(f.category)}] {getattr(f, 'title', '')}"
        for f in b["actionable"][:10]
    ]
    if samples:
        lines.append("Sample findings:")
        lines.extend(samples)
    return "\n".join(lines)


_PROMPT = """You are a GDPR data-protection analyst. A SaaS company at domain \
"{domain}" was scanned for what is publicly visible about it from the outside \
(OSINT recon). Assess its GDPR compliance posture based ONLY on this external \
exposure data:

{brief}

Return STRICT JSON (no prose, no markdown fences) with this exact shape:
{{"summary": "<2-3 sentence plain-English GDPR posture for a non-lawyer founder>",
  "checks": [{{"article": "<GDPR article, e.g. Art. 32>",
    "requirement": "<the obligation in plain English>",
    "passed": <true|false>,
    "detail": "<one specific sentence tied to the findings>"}}]}}
Include 4-6 checks covering at least: security of processing (Art. 32), \
confidentiality/integrity of personal data (Art. 5(1)(f)), and breach \
notification readiness (Art. 33)."""


def _extract_text(result: dict[str, Any]) -> str:
    """Pull human-readable text out of an MCP tools/call result."""
    content = result.get("content")
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("text")]
        if parts:
            return "\n".join(parts)
    for key in ("text", "answer", "output", "result", "message"):
        v = result.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return json.dumps(result)


def _parse_assessment(text: str) -> dict | None:
    """Parse the first JSON object out of Cala's reply and validate its shape."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        return None
    norm: list[dict] = []
    for c in checks:
        if not isinstance(c, dict) or "passed" not in c:
            continue
        norm.append({
            "article": str(c.get("article", "GDPR")),
            "requirement": str(c.get("requirement", "")),
            "passed": bool(c.get("passed")),
            "detail": str(c.get("detail", "")),
        })
    if not norm:
        return None
    summary = str(data.get("summary", "")) or "GDPR posture assessed from your external exposures."
    return {"source": "cala", "summary": summary, "checks": norm}


def _cala_assessment(domain: str, findings: list[Finding]) -> dict | None:
    client = CalaClient()
    if not client.enabled:
        return None
    prompt = _PROMPT.format(domain=domain, brief=_findings_brief(findings))
    try:
        result = client.query(prompt)
    except (CalaError, Exception) as exc:  # noqa: BLE001 - best-effort, never break a report
        logger.warning("Cala GDPR assessment failed, using heuristic: %s", exc)
        return None
    return _parse_assessment(_extract_text(result))


def _signature(findings: list[Finding]) -> str:
    parts = sorted(f"{_val(f.category)}:{_val(f.severity)}" for f in findings)
    return f"{len(findings)}|{'|'.join(parts)}"


def gdpr_assessment(
    domain: str, findings: list[Finding], scan_id: str | None = None
) -> dict:
    """GDPR posture for a scan — Cala-powered when available, heuristic otherwise."""
    cache_key = f"{scan_id}:{_signature(findings)}" if scan_id else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]
    result = _cala_assessment(domain, findings) or heuristic_assessment(findings)
    if cache_key:
        _CACHE[cache_key] = result
    return result
