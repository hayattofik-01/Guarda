from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, ensure_schema
from app.routers import (
    auth,
    cron,
    dashboard,
    documents,
    findings,
    integrations,
    onboarding,
    scans,
    targets,
)

# For the MVP we create tables on startup. Alembic migrations live in
# ``alembic/`` for production use.
Base.metadata.create_all(bind=engine)
ensure_schema()

# After a restart (e.g. an OOM-killed task on a small free-tier box), reclaim
# any scans/documents left stuck "running" so the UI never spins forever.
try:
    from app.services.document_runner import reclaim_stuck_documents
    from app.services.scan_runner import reclaim_stuck_scans

    reclaim_stuck_scans()
    reclaim_stuck_documents()
except Exception:  # noqa: BLE001 - best-effort startup cleanup
    pass

app = FastAPI(title=f"{settings.app_name} API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(targets.router)
app.include_router(scans.router)
app.include_router(findings.router)
app.include_router(dashboard.router)
app.include_router(integrations.router)
app.include_router(onboarding.router)
app.include_router(documents.router)
app.include_router(cron.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
