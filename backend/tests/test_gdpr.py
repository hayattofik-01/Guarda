from types import SimpleNamespace

from app.services import gdpr


def _val(v):
    return SimpleNamespace(value=v)


def _finding(title, severity, category, source="", **kw):
    return SimpleNamespace(
        title=title,
        severity=_val(severity),
        category=_val(category),
        source=_val(source) if source else "",
        location=kw.get("location"),
    )


def test_heuristic_all_clear_passes_every_article():
    result = gdpr.heuristic_assessment([])
    assert result["source"] == "heuristic"
    assert all(c["passed"] for c in result["checks"])
    assert len(result["checks"]) >= 4


def test_heuristic_flags_leaked_secret_and_exposed_data():
    findings = [
        _finding("Leaked AWS key", "high", "sensitive_info", source="gitleaks"),
        _finding("Open backup dir", "medium", "exposed_data", location="/backup/"),
        _finding("Live host", "info", "footprint"),
    ]
    result = gdpr.heuristic_assessment(findings)
    failed = [c for c in result["checks"] if not c["passed"]]
    assert any("32" in c["article"] for c in failed)
    assert any("33" in c["article"] and not c["passed"] for c in result["checks"])


def test_heuristic_flags_harvestable_emails():
    findings = [_finding("staff@acme.io", "low", "sensitive_info", source="theharvester")]
    result = gdpr.heuristic_assessment(findings)
    minimisation = [c for c in result["checks"] if "30" in c["article"]]
    assert minimisation and not minimisation[0]["passed"]


def test_assessment_stays_heuristic_when_cala_unavailable(monkeypatch):
    monkeypatch.setattr(
        gdpr,
        "company_intel",
        lambda domain: {"available": False, "organisation": None, "incidents": []},
    )
    result = gdpr.gdpr_assessment("acme.io", [], scan_id="scan-none")
    assert result["source"] == "heuristic"
    assert result["organisation"] is None
    assert result["incidents"] == []


def test_assessment_enriched_with_cala_incident(monkeypatch):
    intel = {
        "available": True,
        "organisation": {
            "name": "Acme Inc",
            "industry": "SaaS",
            "leadership": [],
            "employees": "200",
        },
        "incidents": [
            {"summary": "2021 breach exposed 1M user records.", "sources": ["https://news/x"]}
        ],
    }
    monkeypatch.setattr(gdpr, "company_intel", lambda domain: intel)
    result = gdpr.gdpr_assessment("acme.io", [], scan_id="scan-cala")
    assert result["source"] == "cala"
    assert result["organisation"]["name"] == "Acme Inc"
    assert result["incidents"][0]["sources"] == ["https://news/x"]
    breach = [c for c in result["checks"] if c["article"] == "Art. 33 · 34"]
    assert breach and breach[0]["passed"] is False
    assert "Acme Inc" in result["summary"]


def test_assessment_cala_no_incident_passes_breach_check(monkeypatch):
    intel = {
        "available": True,
        "organisation": {"name": "Acme Inc", "leadership": []},
        "incidents": [],
    }
    monkeypatch.setattr(gdpr, "company_intel", lambda domain: intel)
    result = gdpr.gdpr_assessment("acme.io", [], scan_id="scan-clean")
    assert result["source"] == "cala"
    breach = [c for c in result["checks"] if c["article"] == "Art. 33 · 34"]
    assert breach and breach[0]["passed"] is True
