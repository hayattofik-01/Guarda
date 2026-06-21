"""GDPR compliance assessment for a scan's external exposures.

A SaaS founder selling to enterprise gets asked "are you GDPR compliant?" on
every security questionnaire. This turns Guarda's external findings into a
plain-English, per-article GDPR posture.

The per-article checks are derived deterministically from the scan's findings so
a report is never blank. **Cala.ai** then enriches the assessment with verified
public intelligence (``app.services.cala_intel``): the organisation behind the
domain is identified and resolved to a verified profile, and publicly reported
cyber incidents feed the Art. 33/34 breach-notification posture (with source
citations). When Cala contributes data the assessment is labelled ``cala``;
otherwise it stays ``heuristic``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.services.cala_intel import company_intel

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


def _apply_intel(base: dict, intel: dict[str, Any]) -> dict:
    """Enrich the deterministic assessment with Cala's verified public intelligence."""
    result = {
        "source": "heuristic",
        "summary": base["summary"],
        "checks": list(base["checks"]),
        "organisation": None,
        "incidents": [],
    }
    if not intel.get("available"):
        return result

    result["source"] = "cala"
    result["organisation"] = intel.get("organisation")
    incidents = intel.get("incidents") or []
    result["incidents"] = incidents

    if incidents:
        detail = incidents[0]["summary"]
        passed = False
    else:
        detail = "Cala found no publicly reported breach affecting this organisation."
        passed = True
    result["checks"].append({
        "article": "Art. 33 · 34",
        "requirement": "No publicly reported breach of personal data on record",
        "passed": passed,
        "detail": detail,
    })

    org = intel.get("organisation") or {}
    org_name = org.get("name")
    verified = f" Organisation verified against Cala public records ({org_name})." if org_name \
        else " Enriched with Cala public records."
    result["summary"] = base["summary"] + verified
    return result


def _signature(findings: list[Finding]) -> str:
    parts = sorted(f"{_val(f.category)}:{_val(f.severity)}" for f in findings)
    return f"{len(findings)}|{'|'.join(parts)}"


def gdpr_assessment(
    domain: str, findings: list[Finding], scan_id: str | None = None
) -> dict:
    """GDPR posture for a scan — deterministic checks enriched with Cala intel."""
    cache_key = f"{scan_id}:{_signature(findings)}" if scan_id else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]
    base = heuristic_assessment(findings)
    intel = company_intel(domain)
    result = _apply_intel(base, intel)
    if cache_key:
        _CACHE[cache_key] = result
    return result
