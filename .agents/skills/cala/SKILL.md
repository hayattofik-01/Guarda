---
name: cala
description: >-
  Use Cala for structured, sourced information about real-world entities,
  including company verification, executive and relationship research, and
  evidence-backed public-intelligence enrichment for Guarda.
compatibility: Requires CALA_API_KEY and internet access.
metadata:
  docs: https://docs.cala.ai
  openapi: https://api.cala.ai/openapi.json
  console: https://console.cala.ai/api-keys
---

# Cala integration skill

## When to use it

Use Cala when Guarda needs verified public facts about an organisation,
people connected to it, ownership relationships, or a public incident. Do not
substitute web scraping or model memory when Cala returns no data: surface the
gap instead.

## Access

Prefer Cala MCP when configured. For the backend REST client, use
`https://api.cala.ai/v1` with `X-API-KEY: <CALA_API_KEY>`; REST endpoints mirror
the MCP tool names. Cala requests may take up to 180 seconds: retry a timeout
once, but never retry HTTP 429 responses.

## Select the smallest correct operation

| Need | Operation |
| --- | --- |
| Filter or list entities by criteria | `knowledge_query` |
| Open-ended research with citations | `knowledge_search` |
| Name to entity ID | `entity_search` |
| Discover available properties/relationships | `entity_introspection` |
| Retrieve a projected profile | `retrieve_entity` |

## Guarda workflow

1. Turn the submitted domain into a candidate company name.
2. Run `entity_search` without a narrow `Company` filter, or use
   `Organization`. For a well-known brand, prefer the brand-level organisation
   result over a legally registered subsidiary; choose using the result
   description and data richness.
3. Run `entity_introspection` on the chosen entity before requesting a field
   projection. Schemas differ by entity.
4. Use `retrieve_entity` with only populated fields required by Guarda:
   legal or display name, industry, employee count, registered address where
   useful, incoming `IS_CEO_OF`/`IS_BOARD_MEMBER_OF`, and outgoing
   `IS_ULTIMATE_PARENT_OF` when available.
5. Use `knowledge_search` for a bounded query about publicly reported cyber
   incidents. Preserve Cala's source provenance in raw finding data.
6. Use `knowledge_query` only for structured, domain-scoped enrichment. Cap
   result size with `limit` and use `return(...)` to avoid unnecessary tokens.
7. Convert an externally verifiable Cala result into a deterministic finding;
   never present absence of Cala data as a security finding.

## Query rules

- Use dot notation for structured filters. `order_by` changes which records
  surface, not merely their presentation.
- A comma in a field filter is an AND condition, not OR.
- Call `entity_introspection` before a projected `retrieve_entity`; do not
  blindly request properties or relationships.
- `knowledge_search` returns cited context. Map its explainability references
  to context origins and retain source URLs when displaying a claim.
- Use `return_entities: false` when no subsequent entity retrieval is needed.

## Failure handling

- Unreachable or no data: return an empty enrichment result and record the
  integration state; do not fabricate a fallback answer.
- Timeout: retry the identical request once with a 180-second timeout.
- Rate limit (429): stop and surface the condition without retrying.
- Keep every request scoped to a customer-authorised domain and its directly
  related organisation/IP evidence.

## MCP tool argument shapes (from `tools/list`)

The Guarda backend talks to the Cala **MCP** server at `CALA_MCP_URL`
(`https://api.cala.ai/mcp/`) via JSON-RPC `tools/call`. Verified input schemas:

- `knowledge_search` — required `input` (natural-language question); optional
  `explainability` (bool), `return_entities` (bool). Returns markdown with
  citations.
- `knowledge_query` — required `input` (dot-notation filter, e.g.
  `startups.location=Spain.funding>10M`); optional `return_entities` (bool).
- `entity_search` — required `name`; optional `entity_types` (array, e.g.
  `["Organization"]`), `limit` (int). Returns entities with IDs.
- `retrieve_entity` — required `entity_id` (UUID); optional `properties`
  (array), `relationships` (object), `numerical_observations` (object).
- `entity_introspection` — required `entity_id` (UUID).

Every `tools/call` result is `{"content": [{"type":"text","text": ...}],
"isError": bool}`. **Always check `isError` first** — an error (e.g. `HTTP 402
Payment Required - Insufficient balance`) comes back with `isError: true` and
must be treated as "no enrichment", never parsed as data.

## Guarda code map

- Client: `backend/app/services/cala.py` (`CalaClient` — one method per MCP
  tool, plus `health()`).
- Enrichment workflow: `backend/app/services/cala_intel.py`
  (`company_intel(domain)` → verified org profile + publicly reported
  incidents; returns an empty result on any failure).
- Used by: `backend/app/services/gdpr.py` — a Cala-verified public incident
  drives the Art. 33 (breach-notification) check and the report shows the
  Cala-verified organisation context; deterministic checks remain the base.

## Gotcha: account balance

A valid key still returns **HTTP 402 "Insufficient balance"** if the Cala
account has no credits. `tools/list` and `initialize` work (so `health()` looks
healthy), but every `tools/call` 402s. Top up at https://console.cala.ai. Until
then Guarda runs entirely on the deterministic fallback.
