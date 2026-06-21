import pytest

from app.services import cala_intel


@pytest.fixture(autouse=True)
def _clear_cache():
    cala_intel._CACHE.clear()
    yield
    cala_intel._CACHE.clear()


def test_candidate_company_name():
    assert cala_intel.candidate_company_name("acme-staging.io") == "Acme Staging"
    assert cala_intel.candidate_company_name("https://www.acme.com/path") == "Acme"
    assert cala_intel.candidate_company_name("foo.co.uk") == "Co"  # naive SLD pick


def test_collect_sources_dedups_and_filters():
    res = {
        "citations": [{"url": "https://a/1"}, {"source_url": "https://a/1"}],
        "nested": {"link": "ftp://skip"},
        "more": [{"href": "https://b/2"}],
    }
    assert cala_intel._collect_sources(res) == ["https://a/1", "https://b/2"]


def test_company_intel_disabled_returns_empty(monkeypatch):
    class Disabled:
        enabled = False

    monkeypatch.setattr(cala_intel, "CalaClient", lambda: Disabled())
    out = cala_intel.company_intel("acme.io")
    assert out["available"] is False
    assert out["organisation"] is None
    assert out["incidents"] == []


def test_company_intel_full_workflow(monkeypatch):
    class Fake:
        enabled = True

        def entity_search(self, name, limit=None, **kw):
            return [{"entity_id": "e1", "name": "Acme Inc"}]

        def entity_introspection(self, entity_id):
            return {"properties": ["legal_name", "industry"], "relationships": ["IS_CEO_OF"]}

        def retrieve_entity(self, entity_id, properties=None, relationships=None):
            return {
                "legal_name": "Acme Incorporated",
                "industry": "SaaS",
                "IS_CEO_OF": [{"name": "Jane Doe"}],
            }

        def knowledge_search(self, input, explainability=False, return_entities=False):
            return {"text": "Acme suffered a breach in 2021.", "citations": [{"url": "https://n/1"}]}

    monkeypatch.setattr(cala_intel, "CalaClient", lambda: Fake())
    out = cala_intel.company_intel("acme.io")
    assert out["available"] is True
    org = out["organisation"]
    assert org["legal_name"] == "Acme Incorporated"
    assert org["industry"] == "SaaS"
    assert org["leadership"] == [{"name": "Jane Doe", "role": "CEO"}]
    assert out["incidents"][0]["sources"] == ["https://n/1"]


def test_company_intel_handles_no_entity(monkeypatch):
    from app.services.cala import CalaError

    class Fake:
        enabled = True

        def entity_search(self, name, limit=None, **kw):
            return []

        def knowledge_search(self, input, explainability=False, return_entities=False):
            raise CalaError("402 Insufficient balance")

    monkeypatch.setattr(cala_intel, "CalaClient", lambda: Fake())
    out = cala_intel.company_intel("acme.io")
    assert out["available"] is False
