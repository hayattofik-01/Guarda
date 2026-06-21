---
name: testing-guarda
description: Test the Guarda SaaS-founder app end-to-end (landing page, A–F dashboard score, add-asset form, questionnaire report). Use when verifying Guarda UI or scoring/report changes.
---

# Testing Guarda

Guarda = "know your external security score (A–F) + questionnaire-ready report for SaaS founders". Stack: FastAPI backend (`:8000`), Next.js frontend (`:3000`), Postgres, Redis, Celery — all via `docker compose`.

## Bring up the stack + seed deterministic data
```bash
cd <repo>
# Use local Postgres (Supabase direct host is IPv6-only and unreachable from CI/containers)
# Ensure SUPABASE_DB_URL is blank in .env so the app falls back to bundled postgres.
docker compose up -d --build
# Seed a verified target + completed scan with 6 findings (score 0 / grade F, all 5 compliance checks fail):
docker compose cp backend/seed_test.py backend:/app/seed_test.py
docker compose exec -T backend python seed_test.py
```
Seed prints the login, target, and scan id. Default test creds: `founder@acme.io` / `guarda123`.

## CRITICAL gotcha: never seed/register an email on a reserved TLD
`UserOut.email` is a pydantic `EmailStr`. Reserved/special-use TLDs (`.test`, `.example`, `.invalid`, `localhost`) are **rejected by the email validator**, so `GET /api/auth/me` returns **500**. Because the frontend auth guard (`components/Shell.tsx`) redirects to `/login` whenever `api.me()` throws, login *appears* to silently fail (token is stored, but every authenticated page bounces back to `/login`).
- Symptom: UI login leaves you on `/login` with fields cleared, no error; `localStorage.guarda_token` is set; `GET /api/auth/me` is 500 while `GET /api/dashboard/stats` is 200.
- Fix: use a normal domain for test accounts (e.g. `@acme.io`, `@example.com` is also fine — only the reserved TLDs above break).
- This might be fixed later by validating emails at registration; if `/me` 500s, check the email domain first.

## Other gotchas
- **Stale 308 redirect for `/`:** an older build redirected `/` → `/login`. Browsers cache 308s aggressively, so after deploying the landing page you may still get redirected. Verify the server with `curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' http://localhost:3000/` (should be `200 ->`). If the browser still redirects, clear browsing data (cached images/files) or load a cache-busting URL like `/?v=2`.
- **Native `<select>` dropdowns** (frequency, verification): click to open, then click the option; confirm via the DOM `selectedindex`/`selected` attributes.
- The frontend reads `NEXT_PUBLIC_API_URL` at **build** time; in compose it's only a runtime env, so the bundle uses the `http://localhost:8000` default — which is correct for browser testing.
- **STALE FRONTEND IMAGE:** `docker compose up -d` does NOT rebuild an already-built `guarda-frontend` image, so newly committed frontend code (e.g. the Cala org-grid render block in `app/reports/[id]/page.tsx`) is missing from the running bundle even though the API returns the data. Symptom: API shows `gdpr.organisation` non-null but the page DOM has no `.cala-org`/`.cala-incidents`. Confirm with `docker compose exec frontend sh -c "grep -rl '<expected text>' /app/.next --include='*.js'"` (only matches when the executable chunks — not just `.js.map` — contain it). Fix: `docker compose up -d --build --no-deps frontend`, then hard-reload (Ctrl+Shift+R).

## Test flow (record browser interactions, annotate with annotate_recording)
1. **Landing (`/`)** — hero "Know your external security score. Close the enterprise deal.", nightmares, pricing €99 vs €100+. Type a domain + "Check my score →" → routes to `/login` and stashes domain in `localStorage["guarda_pending_domain"]`.
2. **Dashboard** — sign in → score hero shows grade badge + N/100 + summary; category tiles (Sensitive/Exposed/Reputation/Footprint).
3. **Add asset (`/targets`)** — domain field prefilled from the landing page; Scan frequency dropdown includes **Hourly**; WhatsApp field persists into the table's WhatsApp column.
4. **Report (`/reports/{scan_id}`)** — grade badge + "External security score · N/100", "Security questionnaire readiness" panel (5 ✓/✗ checks), **"GDPR compliance" panel** (per-article ✓/✗ checks + source badge), Share/Print opens a printable PDF.

## GDPR compliance panel (Cala-enriched, `app/services/gdpr.py` + `app/services/cala_intel.py`)
Every report includes a **GDPR compliance** panel below the security-questionnaire panel. The per-article checks (Art. 5(1)(f)·32, Art. 32, Art. 5(1)(c)·30, Art. 33) are **always derived deterministically from the findings** so the report never breaks. **Cala enriches** the assessment per the `cala` skill (entity intelligence + cited public incidents), it does NOT author the checks:
- `cala_intel.company_intel(domain)` resolves the domain to a verified organisation (`entity_search` → `entity_introspection` → `retrieve_entity`) and researches publicly reported incidents (`knowledge_search`).
- When Cala returns data: badge reads **"Assessed by Cala AI"** (`source: "cala"`); the panel adds an **"Organisation verified by Cala"** fact grid (legal name, industry, employees, HQ, leadership, ultimate parent) and a **"Publicly reported incidents"** list with source links; an extra **Art. 33·34** breach-notification check reflects whether Cala found a public breach.
- When Cala is disabled/errors/402s/finds nothing: badge reads **"Automated assessment"** (`source: "heuristic"`), `organisation: null`, `incidents: []`.

Verify which path ran via the API (don't trust the badge alone):
```bash
curl -s localhost:8000/api/scans/<scan_id>/report -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json;g=json.load(sys.stdin)["gdpr"];print(g["source"]);print("org:",g["organisation"]);print("incidents:",g["incidents"]);[print(c["passed"],c["article"]) for c in g["checks"]]'
```

### Cala gotchas (the live path may be hard to exercise)
- Cala config comes from `.env` (`CALA_API_KEY`, `CALA_MCP_URL=https://api.cala.ai/mcp/`); containers read it via `env_file: .env`. After changing the key, restart: `SUPABASE_DB_URL= docker compose up -d --no-deps backend worker`.
- An **invalid key looks like a URL** (an early placeholder was a 20-char `http...` string) → Cala 401s. A real key is ~48 chars, prefix `clsk`.
- Connectivity check: `GET /api/integrations/cala/health` → `{"enabled":true,"server":{"name":"Cala MCP",...},"tools":[...]}`.
- **Cala may 402 "Insufficient balance"** even with a valid key — the account needs credits. In that case the MCP call returns `{"content":[...],"isError":true}` and Guarda falls back to heuristic. You CANNOT show "Assessed by Cala AI" until the account is topped up; mark that assertion **untested** rather than faking it.
- `gdpr_assessment` caches per `(scan_id, findings-signature)` in-process; restarting the backend clears the cache (useful when re-testing after fixing the key). `cala_intel.company_intel` also caches per-domain in `cala_intel._CACHE`.
- **Pick a demo domain with clean Cala data AND a cited public breach** so a broken integration looks visibly different. `datadoghq.com` works well: clean org (DATADOG, INC. / Software And Services / 6500 / Delaware HQ / single CEO Olivier Pomel) and a well-sourced July 2016 breach. Point the seed target at it via `sed -i 's/acme-staging.io/datadoghq.com/g' backend/seed_test.py` before seeding. Some domains return noisy facts (wrong `legal_name`, junk "X brothers" leaders) or resolve to a same-named but different entity (e.g. `notion.so` → "Notion Capital" VC) — try a few and verify via `cala_intel.company_intel(domain)` in `docker compose exec backend python`.
- Cala property/relationship schema (what `cala_intel` parses): `retrieve_entity` returns `properties: {KEY: {value, sources}}` and `relationships: {incoming|outgoing: {REL: [entities]}}`; `knowledge_search` returns `{content: <markdown answer>, context: [{origins:[{source:{url}}]}]}`. Incidents are asserted only when Cala cites ≥1 source.

## Verifying API directly (fast triage before/while clicking)
```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -d 'username=founder@acme.io&password=guarda123' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"          # must be 200, not 500
curl -s localhost:8000/api/dashboard/stats -H "Authorization: Bearer $TOKEN"  # score/grade/category counts
```

## Out of scope / can't fully verify locally
- Live WhatsApp delivery (needs `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`; send is a best-effort no-op until set).
- Supabase live (direct host IPv6-only; runs on local Postgres fallback).

## Devin Secrets Needed
- `CALA_API_KEY` — powers the live GDPR "Assessed by Cala AI" path (real key ~48 chars, prefix `clsk`; account must have credits or Cala 402s and the panel falls back to heuristic).
- `RESEND_API_KEY` — email alerts (optional for UI flow).
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` — WhatsApp alerts (optional; no-op until set).
- `SUPABASE_DB_URL` — only if testing Supabase live; must be the **Supavisor session pooler** string (IPv4), not the direct `db.<ref>.supabase.co` host.
