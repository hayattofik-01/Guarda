from app.services import enrichment


def test_priority_uses_cvss(monkeypatch):
    monkeypatch.setattr(enrichment, "is_known_exploited", lambda cve: False)
    assert enrichment.compute_priority("high", 7.5, None) == 75.0


def test_priority_falls_back_to_severity(monkeypatch):
    monkeypatch.setattr(enrichment, "is_known_exploited", lambda cve: False)
    assert enrichment.compute_priority("medium", None, None) == 50.0


def test_known_exploited_boosts_priority(monkeypatch):
    monkeypatch.setattr(
        enrichment, "is_known_exploited", lambda cve: cve == "CVE-2021-44228"
    )
    base = enrichment.compute_priority("high", 7.0, "CVE-0000-0000")
    boosted = enrichment.compute_priority("high", 7.0, "CVE-2021-44228")
    assert boosted > base
    assert boosted <= 100.0


def test_priority_capped_at_100(monkeypatch):
    monkeypatch.setattr(enrichment, "is_known_exploited", lambda cve: True)
    assert enrichment.compute_priority("critical", 10.0, "CVE-2021-44228") == 100.0
