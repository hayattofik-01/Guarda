import json

import pytest

from app.services import cala
from app.services.cala import CalaClient, CalaError


def _mcp(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def test_extract_text_joins_content_parts():
    result = {"content": [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]}
    assert cala.extract_text(result) == "hello\nworld"


def test_json_or_text_parses_json_else_returns_text():
    assert cala._json_or_text('{"a": 1}') == {"a": 1}
    assert cala._json_or_text("not json") == "not json"
    assert cala._json_or_text("") == ""


def test_as_entity_list_handles_wrappers():
    assert cala._as_entity_list([{"id": 1}]) == [{"id": 1}]
    assert cala._as_entity_list({"entities": [{"id": 2}]}) == [{"id": 2}]
    assert cala._as_entity_list("nope") == []


def test_entity_search_parses_results(monkeypatch):
    client = CalaClient(api_key="k")
    payload = json.dumps([{"entity_id": "e1", "name": "Acme"}])
    monkeypatch.setattr(client, "call_tool", lambda name, args, **k: _mcp(payload))
    out = client.entity_search("Acme", entity_types=["Organization"])
    assert out[0]["entity_id"] == "e1"


def test_tool_error_result_raises(monkeypatch):
    client = CalaClient(api_key="k")
    monkeypatch.setattr(
        client,
        "call_tool",
        lambda name, args, **k: _mcp("HTTP 402 Insufficient balance", is_error=True),
    )
    with pytest.raises(CalaError):
        client.entity_search("Acme")


def test_retrieve_entity_returns_dict(monkeypatch):
    client = CalaClient(api_key="k")
    payload = json.dumps({"legal_name": "Acme Inc", "industry": "SaaS"})
    monkeypatch.setattr(client, "call_tool", lambda name, args, **k: _mcp(payload))
    out = client.retrieve_entity("e1", properties=["legal_name"])
    assert out["legal_name"] == "Acme Inc"


def test_knowledge_search_returns_dict_with_text(monkeypatch):
    client = CalaClient(api_key="k")
    monkeypatch.setattr(client, "call_tool", lambda name, args, **k: _mcp("Some markdown answer"))
    out = client.knowledge_search("any incidents?")
    assert out["text"] == "Some markdown answer"


def test_disabled_client_raises():
    with pytest.raises(CalaError):
        CalaClient(api_key="").entity_search("Acme")
