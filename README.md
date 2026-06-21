# Guarda

**We watch. We detect. We guide.**

Guarda is a **digital-footprint & sensitive-data exposure monitor**. Add the
domains you own, prove ownership, choose how often Guarda should check them, and
it continuously runs the same free OSINT recon tools attackers use — then turns
whatever it finds into a **plain-language report** and emails you the moment
something sensitive shows up.

Findings are grouped into the things that actually matter to a business:

- **Sensitive Information Found** — leaked passwords, API keys, exposed staff emails
- **Exposed Data Detected** — public `.env`/`.git`, open directories, admin panels, backups
- **Reputation Risk Identified** — subdomain takeovers and leaks that can harm your brand
- **Your Digital Footprint** — the subdomains and live hosts that make up your online presence

> **Legal:** Only monitor assets you own or are explicitly authorized to test.
> Guarda enforces ownership verification (DNS TXT or HTTP file token) before any
> scan can run against a domain.

## Architecture

```
                ┌────────────┐        ┌──────────────┐
   Browser ───▶ │  Next.js   │ ─API─▶ │   FastAPI    │ ──▶ Supabase (Postgres)
                │ dashboard  │        │   backend    │
                └────────────┘        └──────┬───────┘
                                             │ enqueue
                                             ▼
                                      ┌─────────────────────┐   ┌──────────┐
                                      │  Celery workers     │◀─▶│  Redis   │
                                      │  subfinder · httpx  │   └──────────┘
                                      │  nuclei · gitleaks  │
                                      │  theHarvester       │
                                      └──────┬──────────────┘
                                             │ report + alert
                                             ▼
                                      ┌──────────────┐
                                      │   Resend     │  email the user's
                                      │   email      │  alert address
                                      └──────────────┘
```

| Component | Tech |
|---|---|
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2 |
| Async jobs | Celery + Redis |
| Database | Supabase (PostgreSQL), local Postgres fallback |
| Recon tools | subfinder, httpx, nuclei (exposures/misconfig), gitleaks, theHarvester |
| Alerts | Resend email (Slack optional) |
| Frontend | Next.js 14 (App Router), React, TypeScript |
| Packaging | Docker + docker compose |

## How a scan works

1. **subfinder** enumerates subdomains (passive footprint).
2. **httpx** probes which hosts are live and flags risky pages (admin panels, open dirs).
3. **nuclei** runs exposure/misconfig templates on the live endpoints (`.env`, `.git`, backups, leaked tokens, takeovers).
4. **gitleaks** (optional) clones a public GitHub repo you specify and finds committed secrets.
5. **theHarvester** (best-effort) gathers leaked emails/hosts from public sources.
6. Findings are categorized, a **non-technical report** is generated, and if anything sensitive is found, Guarda emails your **alert address** via Resend.

## Quick start

```bash
cp .env.example .env          # set SUPABASE_DB_URL and RESEND_API_KEY (see below)
docker compose up --build
```

- Dashboard: http://localhost:3000
- API docs:  http://localhost:8000/docs

Without `SUPABASE_DB_URL` set, Guarda falls back to the bundled local Postgres
container so you can try it offline.

## Configuration

| Capability | Env var(s) | Notes |
|---|---|---|
| Database | `SUPABASE_DB_URL` | Supabase → Project Settings → Database → Connection string → URI (with password). TLS is applied automatically. Falls back to `DATABASE_URL`. |
| Email alerts | `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | From defaults to Resend's test sender `onboarding@resend.dev`. |
| Report links | `PUBLIC_APP_URL` | Base URL used for the "view full report" link in emails. |
| Scan tuning | `NUCLEI_TAGS`, `NUCLEI_SEVERITY`, `SUBFINDER_MAX_TIME` | Reasonable defaults provided. |
| Optional enrichment | `CALA_API_KEY`, `SHODAN_API_KEY`, `CENSYS_*`, `SECURITYTRAILS_API_KEY`, `VIRUSTOTAL_API_KEY`, `NVD_API_KEY`, `SLACK_WEBHOOK_URL` | Not required. |

## Development

```bash
# backend
cd backend && pip install -e ".[dev]"
ruff check app tests && pytest
uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```
