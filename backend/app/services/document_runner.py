"""In-process document compliance check execution + scheduling + alerting."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Document, ScanStatus, User
from app.services.document_checker import run_document_check
from app.services.notifications import send_document_alert
from app.services.scheduling import next_run

logger = logging.getLogger(__name__)


def process_document(document_id: str) -> str:
    """Run a GDPR compliance check for a document, persist it, alert on gaps."""
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return "document-not-found"

        doc.status = ScanStatus.running
        db.commit()

        try:
            result = run_document_check(doc.filename, doc.content_text or "")

            doc.compliance_status = result["status"]
            doc.compliance_score = result["score"]
            doc.summary = result["summary"]
            doc.result_json = result["result_json"]
            doc.advice = result["advice"]
            doc.status = ScanStatus.completed
            doc.error = None
            now = datetime.now(UTC)
            doc.last_checked_at = now
            doc.next_check_at = next_run(doc.frequency, after=now)
            db.commit()
        except Exception as exc:  # noqa: BLE001 - never leave a doc stuck "running"
            logger.exception("Document check failed for %s", document_id)
            doc.status = ScanStatus.failed
            doc.error = f"Compliance check failed: {exc}"[:500]
            db.commit()
            return "failed"

        if doc.compliance_status != "compliant":
            user = db.get(User, doc.owner_id)
            if user and user.email:
                send_document_alert(user.email, doc.filename, result)
        return doc.compliance_status or "completed"
    finally:
        db.close()


def reclaim_stuck_documents(db=None) -> int:
    """Mark documents stuck in ``queued``/``running`` as failed.

    The in-process background check can be lost if the box restarts/sleeps (or
    was OOM-killed before the fix) mid-check, leaving the document ``running``
    forever and the UI showing "Queued" indefinitely. Any document older than
    ``document_stuck_after_seconds`` is reclaimed so the user can re-check it.
    Returns the number of documents reclaimed.
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.document_stuck_after_seconds)
        # Only reclaim checks that never produced a result; a re-check reuses the
        # row (keeping its old created_at + prior result), so guarding on a null
        # result avoids wrongly failing a freshly queued re-check.
        stale = db.scalars(
            select(Document).where(
                Document.status.in_([ScanStatus.queued, ScanStatus.running]),
                Document.compliance_status.is_(None),
                Document.created_at < cutoff,
            )
        ).all()
        for doc in stale:
            doc.status = ScanStatus.failed
            doc.error = doc.error or (
                "Check did not finish (timed out or interrupted). Re-check to retry."
            )
        if stale:
            db.commit()
        return len(stale)
    finally:
        if owns_session:
            db.close()
