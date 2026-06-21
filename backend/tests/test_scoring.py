from types import SimpleNamespace

from app.services.scoring import compliance_checklist, compute_score, score_from_counts


def _val(v):
    return SimpleNamespace(value=v)


def _finding(severity, category, **kw):
    return SimpleNamespace(
        title=kw.get("title", ""),
        severity=_val(severity),
        category=_val(category),
        source=_val(kw.get("source", "nuclei")),
        location=kw.get("location"),
    )


def test_clean_scan_scores_a():
    result = compute_score([_finding("info", "footprint")])
    assert result["score"] == 100
    assert result["grade"] == "A"


def test_grades_drop_with_severity():
    assert score_from_counts({"critical": 1})["grade"] == "F"
    assert score_from_counts({"medium": 1})["grade"] in ("A", "B")
    assert score_from_counts({"high": 1, "medium": 1})["score"] == 58


def test_footprint_does_not_penalize():
    assert compute_score([_finding("info", "footprint")] * 20)["score"] == 100


def test_compliance_flags_leaked_secrets_and_exposures():
    findings = [
        _finding("high", "sensitive_info", source="gitleaks", title="AWS key"),
        _finding("medium", "exposed_data", title="Open /admin login panel"),
        _finding("info", "footprint", title="sub.example.com"),
    ]
    checks = {c["question"]: c["passed"] for c in compliance_checklist(findings)}
    assert checks["No secrets or credentials leaked in public code"] is False
    assert checks["No private files or folders exposed to the public"] is False
    assert checks["No unprotected admin or login panels"] is False
    assert checks["No subdomains vulnerable to takeover or impersonation"] is True


def test_compliance_all_pass_when_clean():
    checks = compliance_checklist([_finding("info", "footprint")])
    assert all(c["passed"] for c in checks)
