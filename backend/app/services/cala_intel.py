"""Cala-powered public intelligence enrichment for a scanned domain.

Follows the Cala skill's Guarda workflow: turn the domain into a candidate
company name, resolve it to a verified entity (``entity_search`` →
``entity_introspection`` → ``retrieve_entity``), and research publicly reported
cyber incidents (``knowledge_search``). Everything is best-effort: any failure
(unreachable, 402 insufficient balance, 429, timeout, no data) yields an empty
result — Guarda never fabricates facts or treats missing data as a finding.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.cala import CalaClient, CalaError

logger = logging.getLogger(__name__)

# Cache one enrichment per domain so repeated reports don't re-call Cala.
_CACHE: dict[str, dict] = {}

# Fields/relationships we care about, requested only when introspection confirms them.
_WANTED_PROPS = (
    "legal_name", "legalName", "name", "display_name", "industry", "sector",
    "employee_count", "employees", "headcount", "headquarters", "hq",
    "registered_address", "address", "country",
)
_WANTED_RELS = ("IS_CEO_OF", "IS_BOARD_MEMBER_OF", "IS_ULTIMATE_PARENT_OF")


def candidate_company_name(domain: str) -> str:
    """Derive a human company name guess from a domain (e.g. acme-staging.io → Acme Staging)."""
    host = (domain or "").strip().lower()
    host = host.split("//")[-1].split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    labels = [p for p in host.split(".") if p]
    label = labels[-2] if len(labels) >= 2 else (labels[0] if labels else host)
    return label.replace("-", " ").replace("_", " ").strip().title()


def _first(d: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def _resolve_entity(client: CalaClient, name: str) -> dict[str, Any] | None:
    """entity_search preferring Organization; fall back to an unfiltered search."""
    for kwargs in ({"entity_types": ["Organization"]}, {}):
        try:
            results = client.entity_search(name, limit=5, **kwargs)
        except CalaError as exc:
            logger.warning("Cala entity_search failed for %s: %s", name, exc)
            return None
        if results:
            return results[0]
    return None


def _entity_id(entity: dict[str, Any]) -> str | None:
    val = _first(entity, ("entity_id", "id", "uuid"))
    return str(val) if val else None


def _available(introspection: dict[str, Any], wanted: tuple[str, ...]) -> list[str]:
    """Intersect what we want with what the entity's schema actually exposes."""
    names: set[str] = set()
    for key in ("properties", "relationships", "fields", "numerical_observations"):
        section = introspection.get(key)
        if isinstance(section, dict):
            names.update(section.keys())
        elif isinstance(section, list):
            for item in section:
                if isinstance(item, dict):
                    nm = item.get("name") or item.get("key")
                    if nm:
                        names.add(nm)
                elif isinstance(item, str):
                    names.add(item)
    return [w for w in wanted if w in names]


def _people(profile: dict[str, Any], rel: str, role: str) -> list[dict[str, str]]:
    section = profile.get(rel) or profile.get(rel.lower())
    out: list[dict[str, str]] = []
    if isinstance(section, list):
        for item in section:
            if isinstance(item, dict):
                nm = _first(item, ("name", "display_name", "legal_name"))
            else:
                nm = item
            if nm:
                out.append({"name": str(nm), "role": role})
    return out


def _organisation(
    entity: dict[str, Any], profile: dict[str, Any], entity_id: str
) -> dict[str, Any]:
    merged = {**entity, **profile}
    leadership = (
        _people(merged, "IS_CEO_OF", "CEO")
        + _people(merged, "IS_BOARD_MEMBER_OF", "Board member")
    )
    parent = _first(merged, ("IS_ULTIMATE_PARENT_OF", "ultimate_parent", "parent"))
    if isinstance(parent, dict):
        parent = _first(parent, ("name", "legal_name", "display_name"))
    elif isinstance(parent, list) and parent:
        first = parent[0]
        parent = _first(first, ("name", "legal_name")) if isinstance(first, dict) else first
    employees = _first(merged, ("employee_count", "employees", "headcount"))
    hq = _first(merged, ("headquarters", "hq", "registered_address", "address"))
    if isinstance(hq, dict):
        hq = _first(hq, ("name", "formatted", "city", "country"))
    return {
        "entity_id": entity_id,
        "name": str(_first(merged, ("display_name", "name", "legal_name")) or ""),
        "legal_name": _opt_str(_first(merged, ("legal_name", "legalName"))),
        "industry": _opt_str(_first(merged, ("industry", "sector"))),
        "employees": _opt_str(employees),
        "headquarters": _opt_str(hq),
        "leadership": leadership,
        "ultimate_parent": _opt_str(parent),
    }


def _opt_str(v: Any) -> str | None:
    return None if v in (None, "", [], {}) else str(v)


def _incidents(client: CalaClient, name: str) -> list[dict[str, Any]]:
    """knowledge_search for publicly reported cyber incidents, preserving sources."""
    query = (
        f"publicly reported data breaches or cybersecurity incidents involving {name}"
    )
    try:
        res = client.knowledge_search(query, explainability=True, return_entities=False)
    except CalaError as exc:
        logger.warning("Cala knowledge_search failed for %s: %s", name, exc)
        return []
    sources = _collect_sources(res)
    text = (res.get("text") or "").strip() if isinstance(res, dict) else ""
    if not text and not sources:
        return []
    summary = text.split("\n\n")[0][:600] if text else "Publicly reported incident found."
    return [{"summary": summary, "sources": sources}]


def _collect_sources(res: Any) -> list[str]:
    urls: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in ("url", "source_url", "link", "href") and isinstance(v, str):
                    urls.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(res)
    seen: list[str] = []
    for u in urls:
        if u.startswith("http") and u not in seen:
            seen.append(u)
    return seen[:5]


def company_intel(domain: str) -> dict[str, Any]:
    """Verified company profile + publicly reported incidents for a domain (best-effort)."""
    if domain in _CACHE:
        return _CACHE[domain]
    result: dict[str, Any] = {
        "available": False,
        "organisation": None,
        "incidents": [],
        "error": None,
    }
    client = CalaClient()
    if not client.enabled:
        result["error"] = "CALA_API_KEY not set"
        return result

    name = candidate_company_name(domain)
    try:
        entity = _resolve_entity(client, name)
        organisation = None
        if entity:
            eid = _entity_id(entity)
            profile: dict[str, Any] = {}
            if eid:
                try:
                    introspection = client.entity_introspection(eid)
                    props = _available(introspection, _WANTED_PROPS)
                    rels = {r: {} for r in _available(introspection, _WANTED_RELS)}
                    profile = client.retrieve_entity(eid, properties=props, relationships=rels)
                except CalaError as exc:
                    logger.warning("Cala entity retrieval failed for %s: %s", name, exc)
                organisation = _organisation(entity, profile, eid or "")
        incidents = _incidents(client, organisation["name"] if organisation else name)
        result["organisation"] = organisation
        result["incidents"] = incidents
        result["available"] = bool(organisation or incidents)
    except CalaError as exc:
        logger.warning("Cala enrichment failed for %s: %s", domain, exc)
        result["error"] = str(exc)

    _CACHE[domain] = result
    return result
