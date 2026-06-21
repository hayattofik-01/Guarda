"""In-process document compliance check execution + scheduling + alerting."""

from __future__ import annotations

from datetime import UTC, datetime

from app.database import SessionLocal
from app.models import Document, ScanStatus, User
from app.services.document_checker import run_document_check
from app.services.notifications import send_document_alert
from app.services.scheduling import next_run


def process_document(document_id: str) -> str:
    """Run a GDPR compliance check for a document, persist it, alert on gaps."""
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return "document-not-found"

        doc.status = ScanStatus.running
        db.commit()

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

        if doc.compliance_status != "compliant":
            user = db.get(User, doc.owner_id)
            if user and user.email:
                send_document_alert(user.email, doc.filename, result)
        return doc.compliance_status or "completed"
    finally:
        db.close()
