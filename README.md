# Perimeter

Continuous **external vulnerability scanning & attack-surface management** — an open, self-hostable platform inspired by Intruder.io.

Add the assets you own, prove ownership, and Perimeter continuously scans your
internet-facing perimeter for open ports, exposed services, misconfigurations
and known CVEs — then prioritizes the findings and alerts you.

> **Legal:** Only scan assets you own or are explicitly authorized to test.
> Perimeter enforces target ownership verification (DNS TXT or HTTP file token)
> before any scan can run.

## Architecture

```
                ┌────────────┐        ┌──────────────┐
   Browser ───▶ │  Next.js   │ ─API─▶ │   FastAPI    │ ──▶ PostgreSQL
                │ dashboard  │        │   backend    │
                └────────────┘        └──────┬───────┘
                                             │ enqueue
                                             ▼
                                      ┌──────────────┐     ┌──────────┐
                                      │  Celery      │ ◀──▶│  Redis   │
                                      │  workers     │     └──────────┘
                                      │  nmap/nuclei │
                                      └──────┬───────┘
                                             │ enrich
                                             ▼
                                      ┌──────────────┐
                                      │  Cala.ai     │  structured data/intel
                                      │  MCP / API   │  ("skip the data")
                                      └──────────────┘
```

| Component | Tech |
|---|---|
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2, Alembic |
| Async jobs | Celery + Redis |
| Database | PostgreSQL 16 |
| Scanners | nmap (ports/services), nuclei (CVE/templated checks) |
| Data/intel | Cala.ai (MCP/API), pluggable CVE sources (NVD, CISA KEV) |
| Frontend | Next.js 14 (App Router), React, TypeScript |
| Packaging | Docker + docker compose |

## Quick start

```bash
cp .env.example .env          # fill in secrets you have (all optional for MVP)
docker compose up --build
```

- Dashboard: http://localhost:3000
- API docs:  http://localhost:8000/docs

The MVP runs entirely on free, self-hosted tools (nmap + nuclei) — **no API
keys required**. Add keys to `.env` to unlock discovery and enrichment.

## API keys (all optional, enable extra capability)

| Capability | Env var(s) | Provider |
|---|---|---|
| Structured data / intel | `CALA_API_KEY` | cala.ai |
| Asset discovery | `SHODAN_API_KEY`, `CENSYS_API_ID`/`CENSYS_API_SECRET`, `SECURITYTRAILS_API_KEY`, `VIRUSTOTAL_API_KEY` | various |
| CVE intel | `NVD_API_KEY`, `VULNERS_API_KEY` | NIST / Vulners |
| Email alerts | `SENDGRID_API_KEY` | SendGrid |
| Chat alerts | `SLACK_WEBHOOK_URL` | Slack |

See `docs/` for module details.

## Development

```bash
# backend
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload
# frontend
cd frontend && npm install && npm run dev
```
