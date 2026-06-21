"""Cala-powered public intelligence enrichment for a scanned domain.

Follows the Cala skill's Guarda workflow: turn the domain into a candidate
company name, resolve it to a verified entity (``entity_search`` →
``entity_introspection`` → ``retrieve_entity``), and research publicly reported
cyber incidents (``knowledge_search``). Everything is best-effort: any failure
(unreachable, 402 insufficient balance, 429, timeout, no data) yields an empty
result — Guarda never fabricates facts or treats missing data as a finding.

Cala's ``retrieve_entity`` returns properties as ``{name: {value, sources}}`` and
relationships nested under ``{"incoming": {...}, "outgoing": {...}}``, each a map
of relationship name → list of related entities. ``knowledge_search`` returns a
markdown ``content`` answer plus a ``context`` list whose ``origins`` carry the
source URLs; an incident is only asserted when Cala cites at least one source.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.cala import CalaClient, CalaError

logger = logging.getLogger(__name__)

# Cache one enrichment per domain so repeated reports don't re-call Cala.
_CACHE: dict[str, dict] = {}

# Entity properties we surface, requested only when introspection confirms them.
_WANTED_PROPS = (
    "legal_name",
    "name",
    "employee_count",
    "registered_address",
    "website",
    "founding_date",
)
# Incoming relationships → leadership roles.
_LEADER_RELS = {"IS_CEO_OF": "CEO", "IS_BOARD_MEMBER_OF": "Board member"}
# Outgoing relationships we care about.
_INDUSTRY_REL = "OPERATES_IN_INDUSTRY"
_PARENT_REL = "IS_ULTIMATE_PARENT_OF"


def candidate_company_name(domain: str) -> str:
    """Derive a human company name guess from a domain (e.g. acme-staging.io → Acme Staging)."""
    host = (domain or "").strip().lower()
    host = host.split("//")[-1].split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    labels = [p for p in host.split(".") if p]
    label = labels[-2] if len(labels) >= 2 else (labels[0] if labels else host)
    return label.replace("-", " ").replace("_", " ").strip().title()


def _opt_str(v: Any) -> str | None:
    return None if v in (None, "", [], {}) else str(v)


def _pretty(name: str) -> str:
    return name.replace("_", " ").strip().title()


def _names(seq: Any) -> list[str]:
    out: list[str] = []
    for x in seq or []:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            nm = x.get("name") or x.get("key")
            if nm:
                out.append(nm)
    return out


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
    val = entity.get("entity_id") or entity.get("id") or entity.get("uuid")
    return str(val) if val else None


def _avail_props(introspection: dict[str, Any], wanted: tuple[str, ...]) -> list[str]:
    section = introspection.get("properties")
    if isinstance(section, dict):
        names = set(section.keys())
    else:
        names = set(_names(section))
    return [w for w in wanted if w in names]


def _rel_directions(introspection: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return (incoming, outgoing) relationship names exposed by the entity schema."""
    rels = introspection.get("relationships")
    if isinstance(rels, dict) and ("incoming" in rels or "outgoing" in rels):
        return set(_names(rels.get("incoming"))), set(_names(rels.get("outgoing")))
    both = set(rels.keys()) if isinstance(rels, dict) else set(_names(rels))
    return both, both


def _prop(profile: dict[str, Any], key: str) -> str | None:
    props = profile.get("properties") or {}
    v = props.get(key)
    if isinstance(v, dict):
        v = v.get("value")
    return _opt_str(v)


def _rel_items(profile: dict[str, Any], direction: str, rel: str) -> list[dict[str, Any]]:
    rels = profile.get("relationships") or {}
    section = rels.get(direction) or {}
    items = section.get(rel) if isinstance(section, dict) else None
    return [it for it in items if isinstance(it, dict)] if isinstance(items, list) else []


def _organisation(
    entity: dict[str, Any], profile: dict[str, Any], entity_id: str
) -> dict[str, Any]:
    leadership: list[dict[str, str]] = []
    seen_leaders: set[str] = set()
    for rel, role in _LEADER_RELS.items():
        for it in _rel_items(profile, "incoming", rel):
            nm = it.get("name")
            if nm and str(nm) not in seen_leaders:
                seen_leaders.add(str(nm))
                leadership.append({"name": str(nm), "role": role})
    leadership = leadership[:5]

    industries = [
        _pretty(it["name"])
        for it in _rel_items(profile, "outgoing", _INDUSTRY_REL)
        if it.get("name")
    ]
    industry = ", ".join(dict.fromkeys(industries[:3])) or None

    parents = [
        it.get("name")
        for it in _rel_items(profile, "outgoing", _PARENT_REL)
        if it.get("name")
    ]
    ultimate_parent = _opt_str(parents[0]) if parents else None

    return {
        "entity_id": entity_id,
        "name": str(profile.get("name") or entity.get("name") or ""),
        "legal_name": _prop(profile, "legal_name"),
        "industry": industry,
        "employees": _prop(profile, "employee_count"),
        "headquarters": _prop(profile, "registered_address"),
        "leadership": leadership,
        "ultimate_parent": ultimate_parent,
    }


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


def _summarise(content: str) -> str:
    """First substantive paragraph of Cala's markdown answer (skip headings)."""
    for block in content.split("\n\n"):
        block = block.strip()
        if block and not block.startswith("#"):
            return block[:600]
    return content.strip()[:600]


def _incidents(client: CalaClient, name: str) -> list[dict[str, Any]]:
    """knowledge_search for publicly reported cyber incidents; assert only when cited."""
    query = f"publicly reported data breaches or cybersecurity incidents involving {name}"
    try:
        res = client.knowledge_search(query, explainability=True, return_entities=False)
    except CalaError as exc:
        logger.warning("Cala knowledge_search failed for %s: %s", name, exc)
        return []
    if not isinstance(res, dict):
        return []
    sources = _collect_sources(res)
    if not sources:  # never present absence of cited data as a finding
        return []
    summary = _summarise(res.get("content") or "") or "Publicly reported incident found."
    return [{"summary": summary, "sources": sources}]


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
                    props = _avail_props(introspection, _WANTED_PROPS)
                    inc_avail, out_avail = _rel_directions(introspection)
                    rel_arg: dict[str, Any] = {}
                    incoming = {r: {} for r in _LEADER_RELS if r in inc_avail}
                    outgoing = {r: {} for r in (_INDUSTRY_REL, _PARENT_REL) if r in out_avail}
                    if incoming:
                        rel_arg["incoming"] = incoming
                    if outgoing:
                        rel_arg["outgoing"] = outgoing
                    profile = client.retrieve_entity(
                        eid, properties=props, relationships=rel_arg or None
                    )
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
