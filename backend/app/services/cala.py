"""Cala.ai integration — the structured data / intel layer ("skip the data").

Cala exposes a Model Context Protocol (MCP) server over streamable HTTP at
``https://api.cala.ai/mcp/`` authenticated with an ``X-API-KEY`` header. Instead
of scraping the web for context about a target (the organization behind a
domain, regulatory/sanctions/registry data, etc.), we query Cala for verified,
structured facts and use them to enrich and prioritize findings.

The client speaks JSON-RPC 2.0. Responses may come back as plain JSON or as an
SSE (``text/event-stream``) body; both are handled.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

PROTOCOL_VERSION = "2024-11-05"


class CalaError(RuntimeError):
    pass


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
            # Concatenate SSE data lines and parse the last JSON payload.
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
        self, client: httpx.Client, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            body["params"] = params
        resp = client.post(self.url, headers=self._headers(), json=body, timeout=30)
        if resp.status_code == 401:
            raise CalaError("Invalid Cala API key (401)")
        resp.raise_for_status()
        data = self._parse(resp)
        if "error" in data:
            raise CalaError(str(data["error"]))
        return data.get("result", {})

    def health(self) -> dict[str, Any]:
        """Initialize a session and list available tools — used as a connectivity check."""
        if not self.enabled:
            return {"enabled": False, "error": "CALA_API_KEY not set"}
        try:
            with httpx.Client() as client:
                info = self._rpc(
                    client,
                    "initialize",
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "perimeter", "version": "0.1.0"},
                    },
                )
                tools = self._rpc(client, "tools/list")
                tool_names = [t.get("name") for t in tools.get("tools", [])]
                return {
                    "enabled": True,
                    "server": info.get("serverInfo", {}),
                    "tools": tool_names,
                }
        except (CalaError, httpx.HTTPError) as exc:
            return {"enabled": True, "error": str(exc)}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise CalaError("CALA_API_KEY not set")
        with httpx.Client() as client:
            self._rpc(
                client,
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "perimeter", "version": "0.1.0"},
                },
            )
            return self._rpc(client, "tools/call", {"name": name, "arguments": arguments})

    def query(self, prompt: str) -> dict[str, Any]:
        """Best-effort free-text query against Cala.

        Tool names are discovered at runtime; we pick the first tool that looks
        like a query/search entrypoint and forward the prompt.
        """
        if not self.enabled:
            raise CalaError("CALA_API_KEY not set")
        with httpx.Client() as client:
            self._rpc(
                client,
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "perimeter", "version": "0.1.0"},
                },
            )
            tools = self._rpc(client, "tools/list").get("tools", [])
            tool = _pick_query_tool(tools)
            if tool is None:
                raise CalaError("No query-like tool exposed by Cala")
            arg_key = _pick_query_arg(tool)
            return self._rpc(
                client, "tools/call", {"name": tool["name"], "arguments": {arg_key: prompt}}
            )


def _pick_query_tool(tools: list[dict[str, Any]]) -> dict[str, Any] | None:
    for keyword in ("query", "search", "ask", "answer"):
        for tool in tools:
            if keyword in (tool.get("name") or "").lower():
                return tool
    return tools[0] if tools else None


def _pick_query_arg(tool: dict[str, Any]) -> str:
    schema = tool.get("inputSchema", {}) or {}
    props = schema.get("properties", {}) or {}
    for candidate in ("query", "q", "prompt", "question", "text", "input"):
        if candidate in props:
            return candidate
    return next(iter(props), "query")
