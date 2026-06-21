"""External security score (A–F) and compliance posture.

Turns a scan's findings into a single, founder-friendly grade plus a
security-questionnaire-style checklist a SaaS owner can hand to an enterprise
prospect. Footprint findings are context, not penalties.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Finding

# Penalty applied to the 100-point score per open finding, by severity.
_PENALTY = {"critical": 50, "high": 30, "medium": 12, "low": 4, "info": 0}

GRADE_SUMMARY = {
    "A": "Strong — nothing urgent is exposed to the public right now.",
    "B": "Good — only a few low-risk items to tidy up.",
    "C": "Fair — some exposures an enterprise security review would flag.",
    "D": "Weak — exposures here will likely fail a security questionnaire.",
    "F": "At risk — sensitive data or critical exposures are publicly visible.",
}


def _val(x) -> str:
    return x.value if hasattr(x, "value") else x


def grade_for(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def score_from_counts(by_severity: dict[str, int]) -> dict:
    """Compute the score from a {severity: count} map (footprint/info = 0)."""
    penalty = sum(_PENALTY.get(sev, 0) * count for sev, count in by_severity.items())
    score = max(0, min(100, 100 - penalty))
    grade = grade_for(score)
    return {"score": score, "grade": grade, "summary": GRADE_SUMMARY[grade]}


def compute_score(findings: list[Finding]) -> dict:
    """Compute the A–F score from a list of findings."""
    counts: dict[str, int] = {}
    for f in findings:
        if _val(f.category) == "footprint":
            continue
        sev = _val(f.severity)
        counts[sev] = counts.get(sev, 0) + 1
    return score_from_counts(counts)


def _text(f) -> str:
    return f"{f.title or ''} {getattr(f, 'location', '') or ''}".lower()


def compliance_checklist(findings: list[Finding]) -> list[dict]:
    """Map findings to common security-questionnaire questions (pass/fail)."""
    actionable = [f for f in findings if _val(f.category) != "footprint"]

    leaked_secrets = [
        f for f in actionable
        if _val(getattr(f, "source", "")) == "gitleaks"
        or (
            _val(f.category) == "sensitive_info"
            and any(k in _text(f) for k in ("secret", "key", "token", "password", "credential"))
        )
    ]
    exposed = [f for f in actionable if _val(f.category) == "exposed_data"]
    admin_kw = ("admin", "login", "panel", "dashboard")
    admin_panels = [f for f in exposed if any(k in _text(f) for k in admin_kw)]
    leaked_emails = [
        f for f in actionable
        if _val(getattr(f, "source", "")) == "theharvester" and _val(f.category) == "sensitive_info"
    ]
    takeover = [f for f in actionable if _val(f.category) == "reputation_risk"]

    def check(question: str, offenders: list, clear: str) -> dict:
        passed = len(offenders) == 0
        return {
            "question": question,
            "passed": passed,
            "detail": clear if passed else f"{len(offenders)} issue(s) found — see the report.",
        }

    return [
        check("No secrets or credentials leaked in public code", leaked_secrets,
              "No leaked secrets detected."),
        check("No private files or folders exposed to the public", exposed,
              "No exposed files or directories."),
        check("No unprotected admin or login panels", admin_panels,
              "No public admin interfaces."),
        check("No staff emails harvestable for phishing", leaked_emails,
              "No harvestable corporate emails."),
        check("No subdomains vulnerable to takeover or impersonation", takeover,
              "No takeover-able subdomains."),
    ]
