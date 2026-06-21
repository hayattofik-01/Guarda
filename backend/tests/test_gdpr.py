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
    # security-of-processing (Art. 32) checks should fail
    assert any("32" in c["article"] for c in failed)
    # breach-notification readiness fails because of the high-severity exposure
    assert any("33" in c["article"] and not c["passed"] for c in result["checks"])


def test_heuristic_flags_harvestable_emails():
    findings = [_finding("staff@acme.io", "low", "sensitive_info", source="theharvester")]
    result = gdpr.heuristic_assessment(findings)
    minimisation = [c for c in result["checks"] if "30" in c["article"]]
    assert minimisation and not minimisation[0]["passed"]


def test_parse_assessment_extracts_json_from_noise():
    text = 'Sure! Here is the result:\n{"summary": "ok", "checks": [' \
        '{"article": "Art. 32", "requirement": "secure", "passed": false, "detail": "x"}]}'
    parsed = gdpr._parse_assessment(text)
    assert parsed is not None
    assert parsed["source"] == "cala"
    assert parsed["checks"][0]["passed"] is False
    assert parsed["checks"][0]["article"] == "Art. 32"


def test_parse_assessment_rejects_garbage():
    assert gdpr._parse_assessment("no json here") is None
    assert gdpr._parse_assessment('{"summary": "x"}') is None


def test_extract_text_from_mcp_content():
    result = {"content": [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]}
    assert gdpr._extract_text(result) == "hello\nworld"


def test_assessment_falls_back_to_heuristic_when_cala_disabled(monkeypatch):
    monkeypatch.setattr(gdpr, "_cala_assessment", lambda *a, **k: None)
    result = gdpr.gdpr_assessment("acme.io", [], scan_id="scan-xyz")
    assert result["source"] == "heuristic"
