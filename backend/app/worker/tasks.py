from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Frequency,
    Scan,
    ScanStatus,
    Target,
    TargetStatus,
)
from app.services.scan_runner import execute_scan
from app.worker.celery_app import celery_app

# How often each frequency triggers an automated scan.
FREQUENCY_INTERVALS = {
    Frequency.hourly: timedelta(hours=1),
    Frequency.daily: timedelta(days=1),
    Frequency.weekly: timedelta(weeks=1),
    Frequency.monthly: timedelta(days=30),
}


@celery_app.task(name="app.worker.tasks.run_scan")
def run_scan(scan_id: str) -> str:
    """Celery wrapper around the in-process scan runner (worker deployment)."""
    return execute_scan(scan_id)


@celery_app.task(name="app.worker.tasks.enqueue_due_scans")
def enqueue_due_scans() -> int:
    """Periodic task: enqueue scans for verified assets whose frequency is due."""
    db = SessionLocal()
    enqueued = 0
    try:
        now = datetime.now(UTC)
        targets = db.scalars(
            select(Target).where(Target.status == TargetStatus.verified)
        )
        for target in targets:
            interval = FREQUENCY_INTERVALS.get(target.frequency)
            if interval is None:
                continue
            last = db.scalar(
                select(Scan)
                .where(Scan.target_id == target.id)
                .order_by(Scan.created_at.desc())
            )
            last_time = last.created_at if last else None
            if last_time is not None and last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=UTC)
            if last_time is None or now - last_time >= interval:
                scan = Scan(target_id=target.id, status=ScanStatus.queued)
                db.add(scan)
                db.commit()
                db.refresh(scan)
                result = run_scan.delay(scan.id)
                scan.celery_task_id = result.id
                db.commit()
                enqueued += 1
        return enqueued
    finally:
        db.close()
