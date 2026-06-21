from types import SimpleNamespace

from app.services.report import build_report, render_email_html


def _val(v):
    return SimpleNamespace(value=v)


def _finding(title, severity, category, **kw):
    return SimpleNamespace(
        title=title,
        severity=_val(severity),
        category=_val(category),
        location=kw.get("location"),
        host=kw.get("host"),
        description=kw.get("description", ""),
        remediation=kw.get("remediation", ""),
    )


def _make(findings):
    target = SimpleNamespace(address="example.com", label="My site")
    scan = SimpleNamespace(id="scan-123")
    return build_report(target, scan, findings)


def test_report_all_clear():
    report = _make([])
    assert report["overall_risk"] == "All clear"
    assert report["totals"]["findings"] == 0
    assert report["sections"] == []


def test_report_action_needed_and_sections_ordered():
    findings = [
        _finding("Live host", "info", "footprint", host="example.com"),
        _finding("Leaked AWS key", "high", "sensitive_info", location="app.js"),
        _finding("Open dir", "medium", "exposed_data", location="/backup/"),
    ]
    report = _make(findings)
    assert report["overall_risk"] == "Action needed"
    # sensitive_info section comes before exposed_data and footprint
    cats = [s["category"] for s in report["sections"]]
    assert cats.index("sensitive_info") < cats.index("exposed_data") < cats.index("footprint")
    assert report["totals"]["sensitive_information"] == 1


def test_render_email_html_includes_brand_and_link():
    report = _make([_finding("Leaked key", "high", "sensitive_info", location="x")])
    html = render_email_html(report, "https://app.example/reports/scan-123")
    assert "GUARDA" in html
    assert "https://app.example/reports/scan-123" in html
