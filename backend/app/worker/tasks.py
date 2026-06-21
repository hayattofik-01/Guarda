from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Finding,
    Scan,
    ScanStatus,
    Severity,
    Target,
    TargetStatus,
)
from app.services.enrichment import compute_priority, is_known_exploited
from app.worker.celery_app import celery_app
from app.worker.scanners import nmap_scan, nuclei_scan

# Recognized schedule keywords -> minimum interval between automated scans.
SCHEDULE_INTERVALS = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


@celery_app.task(name="app.worker.tasks.run_scan")
def run_scan(scan_id: str) -> str:
    db = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        if scan is None:
            return "scan-not-found"
        target = db.get(Target, scan.target_id)
        if target is None:
            scan.status = ScanStatus.failed
            scan.error = "Target not found"
            db.commit()
            return "target-not-found"

        scan.status = ScanStatus.running
        scan.started_at = datetime.now(UTC)
        db.commit()

        raw_chunks: list[str] = []
        all_findings: list[dict] = []
        errors: list[str] = []

        for scanner in (nmap_scan, nuclei_scan):
            name = scanner.__name__.split(".")[-1]
            if not scanner.available():
                errors.append(f"{name}: not installed, skipped")
                continue
            try:
                findings, raw = scanner.run(target.address)
                all_findings.extend(findings)
                raw_chunks.append(f"### {name}\n{raw}")
            except Exception as exc:  # noqa: BLE001 - record and continue
                errors.append(f"{name}: {exc}")

        for data in all_findings:
            severity = Severity(data.get("severity", "info"))
            cve_id = data.get("cve_id")
            cvss = data.get("cvss_score")
            priority = compute_priority(severity.value, cvss, cve_id)
            description = data.get("description")
            if is_known_exploited(cve_id):
                kev_note = "[KEV] Actively exploited per CISA Known-Exploited-Vulnerabilities."
                description = f"{kev_note} {description or ''}".strip()
            db.add(
                Finding(
                    scan_id=scan.id,
                    title=data["title"],
                    description=description,
                    severity=severity,
                    host=data.get("host"),
                    port=data.get("port"),
                    service=data.get("service"),
                    source=data.get("source", "nmap"),
                    cve_id=cve_id,
                    cvss_score=cvss,
                    priority_score=priority,
                    remediation=data.get("remediation"),
                    reference=data.get("reference"),
                )
            )

        scan.raw_output = "\n\n".join(raw_chunks)[:500_000]
        scan.finished_at = datetime.now(UTC)
        if all_findings or not errors:
            scan.status = ScanStatus.completed
        else:
            scan.status = ScanStatus.failed
        if errors:
            scan.error = "; ".join(errors)
        db.commit()

        _notify(target, len(all_findings))
        return scan.status.value
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.enqueue_due_scans")
def enqueue_due_scans() -> int:
    """Periodic task: enqueue scans for verified targets whose schedule is due."""
    db = SessionLocal()
    enqueued = 0
    try:
        now = datetime.now(UTC)
        targets = db.scalars(
            select(Target).where(
                Target.status == TargetStatus.verified, Target.schedule.is_not(None)
            )
        )
        for target in targets:
            interval = SCHEDULE_INTERVALS.get((target.schedule or "").lower())
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


def _notify(target: Target, finding_count: int) -> None:
    """Best-effort Slack/email alert. No-op when not configured."""
    from app.services.notifications import send_scan_complete

    try:
        send_scan_complete(target.address, finding_count)
    except Exception:
        pass
