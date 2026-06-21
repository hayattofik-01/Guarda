"""Scheduler endpoint — the engine behind Guarda's always-on monitoring.

An external free scheduler (a GitHub Actions cron) calls ``/api/cron/tick`` with
the shared ``X-Cron-Secret``. The tick runs every domain scan and document check
that is due based on each account's chosen interval, refreshes any pending Devin
advice, and (via the runners) emails the owner when something is off.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from sqlalchemy import or_, select

from app.config import settings
from app.database import SessionLocal
from app.models import Document, Scan, ScanStatus, Target, TargetStatus
from app.services.scheduling import next_run

router = APIRouter(prefix="/api/cron", tags=["cron"])

_BATCH = 25


def _authorize(secret: str | None) -> None:
    if not settings.cron_secret:
        raise HTTPException(status_code=503, detail="Scheduler is not configured.")
    if secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret.")


@router.post("/tick")
def tick(
    background: BackgroundTasks,
    x_cron_secret: str | None = Header(default=None),
) -> dict:
    """Run all due scans + document checks; refresh pending advice."""
    _authorize(x_cron_secret)
    now = datetime.now(UTC)
    db = SessionLocal()
    try:
        scans_started = _run_due_scans(db, background, now)
        docs_started = _run_due_documents(db, background, now)
        advice_refreshed = _refresh_pending_advice(db)
        db.commit()
        return {
            "ran_at": now.isoformat(),
            "scans_started": scans_started,
            "documents_checked": docs_started,
            "advice_refreshed": advice_refreshed,
        }
    finally:
        db.close()


def _run_due_scans(db, background: BackgroundTasks, now: datetime) -> int:
    due_targets = list(
        db.scalars(
            select(Target)
            .where(
                Target.status == TargetStatus.verified,
                or_(Target.next_scan_at.is_(None), Target.next_scan_at <= now),
            )
            .limit(_BATCH)
        )
    )
    count = 0
    from app.services.scan_runner import execute_scan

    for target in due_targets:
        scan = Scan(target_id=target.id, status=ScanStatus.queued)
        db.add(scan)
        # Push the next due time forward now so the following tick won't re-queue
        # this target while the scan is still running. execute_scan resets it on
        # completion.
        target.next_scan_at = next_run(target.frequency, after=now)
        db.flush()
        background.add_task(execute_scan, scan.id)
        count += 1
    return count


def _run_due_documents(db, background: BackgroundTasks, now: datetime) -> int:
    due_docs = list(
        db.scalars(
            select(Document)
            .where(
                Document.next_check_at.is_not(None),
                Document.next_check_at <= now,
                Document.status != ScanStatus.running,
            )
            .limit(_BATCH)
        )
    )
    count = 0
    from app.services.document_runner import process_document

    for doc in due_docs:
        doc.next_check_at = next_run(doc.frequency, after=now)
        db.flush()
        background.add_task(process_document, doc.id)
        count += 1
    return count


def _refresh_pending_advice(db) -> int:
    pending = list(
        db.scalars(
            select(Scan).where(Scan.advice_status == "pending").limit(_BATCH)
        )
    )
    from app.services.advice_agent import refresh_advice

    return sum(1 for scan in pending if refresh_advice(scan))
