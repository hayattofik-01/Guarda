"""Cala.ai integration — the structured data / intel layer ("skip the data").

Cala exposes a Model Context Protocol (MCP) server over streamable HTTP at
``https://api.cala.ai/mcp/`` authenticated with an ``X-API-KEY`` header. Instead
of scraping the web for context about a target (the organization behind a
domain, its leadership/ownership, publicly reported incidents, etc.), we query
Cala for verified, structured facts and use them to enrich findings.

This client exposes one method per Cala MCP tool — ``entity_search``,
``entity_introspection``, ``retrieve_entity``, ``knowledge_search`` and
``knowledge_query`` — matching the documented input schemas. The transport
speaks JSON-RPC 2.0; responses may come back as plain JSON or as an SSE
(``text/event-stream``) body, both handled here.

Failure handling follows the Cala skill: requests may take up to 180s, a
timeout is retried once, and HTTP 429 is surfaced without retrying. Every
``tools/call`` result carries an ``isError`` flag — callers must treat an error
result (e.g. ``402 Insufficient balance``) as "no data", never as a fact.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

PROTOCOL_VERSION = "2024-11-05"
DEFAULT_TIMEOUT = 180.0


class CalaError(RuntimeError):
    pass


class CalaRateLimited(CalaError):
    """HTTP 429 from Cala — per the skill, surface without retrying."""


class CalaClient:
    def __init__(self, api_key: str | None = None, url: str | None = None) -> None:
        self.api_key = api_key or settings.cala_api_key
        self.url = url or settings.cala_mcp_url
        self._id = 0

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    @staticmethod
    def _parse(resp: httpx.Response) -> dict[str, Any]:
        ctype = resp.headers.get("content-type", "")
        if "text/event-stream" in ctype:
            payload: dict[str, Any] = {}
            for line in resp.text.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    chunk = line[len("data:"):].strip()
                    if chunk and chunk != "[DONE]":
                        try:
                            payload = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
            return payload
        return resp.json()

    def _rpc(
        self,
        client: httpx.Client,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            body["params"] = params
        resp = client.post(self.url, headers=self._headers(), json=body)
        if resp.status_code == 401:
            raise CalaError("Invalid Cala API key (401)")
        if resp.status_code == 429:
            raise CalaRateLimited("Cala rate limit (429)")
        resp.raise_for_status()
        data = self._parse(resp)
        if "error" in data:
            raise CalaError(str(data["error"]))
        return data.get("result", {})

    def _init(self, client: httpx.Client) -> dict[str, Any]:
        return self._rpc(
            client,
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "guarda", "version": "0.1.0"},
            },
        )

    def health(self) -> dict[str, Any]:
        """Initialize a session and list available tools — a connectivity check."""
        if not self.enabled:
            return {"enabled": False, "error": "CALA_API_KEY not set"}
        try:
            with httpx.Client(timeout=30) as client:
                info = self._init(client)
                tools = self._rpc(client, "tools/list")
                tool_names = [t.get("name") for t in tools.get("tools", [])]
                return {
                    "enabled": True,
                    "server": info.get("serverInfo", {}),
                    "tools": tool_names,
                }
        except (CalaError, httpx.HTTPError) as exc:
            return {"enabled": True, "error": str(exc)}

    def call_tool(
        self, name: str, arguments: dict[str, Any], timeout: float = DEFAULT_TIMEOUT
    ) -> dict[str, Any]:
        """Raw ``tools/call`` (init + call). Retries once on timeout, never on 429.

        Returns the MCP result dict (which may carry ``isError: true``).
        """
        if not self.enabled:
            raise CalaError("CALA_API_KEY not set")
        last_exc: httpx.TimeoutException | None = None
        for _ in range(2):
            try:
                with httpx.Client(timeout=timeout) as client:
                    self._init(client)
                    return self._rpc(client, "tools/call", {"name": name, "arguments": arguments})
            except httpx.TimeoutException as exc:
                last_exc = exc
                continue
        raise CalaError(f"Cala timed out calling {name}") from last_exc

    def _tool_data(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool and return parsed data, raising CalaError on an error result."""
        result = self.call_tool(name, arguments)
        if result.get("isError"):
            raise CalaError(f"Cala tool '{name}' error: {extract_text(result)[:200]}")
        return _json_or_text(extract_text(result))

    # --- one method per documented Cala MCP tool -------------------------------

    def entity_search(
        self, name: str, entity_types: list[str] | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {"name": name}
        if entity_types:
            args["entity_types"] = entity_types
        if limit is not None:
            args["limit"] = limit
        return _as_entity_list(self._tool_data("entity_search", args))

    def entity_introspection(self, entity_id: str) -> dict[str, Any]:
        data = self._tool_data("entity_introspection", {"entity_id": entity_id})
        return data if isinstance(data, dict) else {"raw": data}

    def retrieve_entity(
        self,
        entity_id: str,
        properties: list[str] | None = None,
        relationships: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"entity_id": entity_id}
        if properties:
            args["properties"] = properties
        if relationships:
            args["relationships"] = relationships
        data = self._tool_data("retrieve_entity", args)
        return data if isinstance(data, dict) else {"raw": data}

    def knowledge_search(
        self, input: str, explainability: bool = False, return_entities: bool = False
    ) -> dict[str, Any]:
        args = {
            "input": input,
            "explainability": explainability,
            "return_entities": return_entities,
        }
        data = self._tool_data("knowledge_search", args)
        if isinstance(data, dict):
            return data
        return {"text": str(data)}

    def knowledge_query(self, input: str, return_entities: bool = False) -> Any:
        args = {"input": input, "return_entities": return_entities}
        return self._tool_data("knowledge_query", args)


def extract_text(result: dict[str, Any]) -> str:
    """Pull human-readable text out of an MCP ``tools/call`` result."""
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


def _json_or_text(text: str) -> Any:
    """Best-effort: parse a JSON payload out of ``text``, else return the raw string."""
    text = (text or "").strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _as_entity_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    if isinstance(data, dict):
        for key in ("entities", "results", "data", "items"):
            v = data.get(key)
            if isinstance(v, list):
                return [e for e in v if isinstance(e, dict)]
    return []
