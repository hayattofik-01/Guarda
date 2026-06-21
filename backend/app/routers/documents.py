from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, ScanStatus, User
from app.schemas import DocumentDetail, DocumentOut
from app.services.document_checker import extract_text

router = APIRouter(prefix="/api/documents", tags=["documents"])

_MAX_BYTES = 8 * 1024 * 1024  # 8 MB


def _owned_document(document_id: str, user: User, db: Session) -> Document:
    doc = db.get(Document, document_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form("document"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    """Upload a contract/policy; Guarda extracts its text and checks it for GDPR
    clauses automatically, then re-checks it on the account's schedule."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 8 MB).")

    content_text = extract_text(file.filename or "document", raw)

    doc = Document(
        owner_id=user.id,
        filename=file.filename or "document",
        doc_type=doc_type or "document",
        content_text=content_text[:1_000_000],
        status=ScanStatus.queued,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    from app.services.document_runner import process_document

    background.add_task(process_document, doc.id)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.owner_id == user.id)
            .order_by(Document.created_at.desc())
        )
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    doc = _owned_document(document_id, user, db)
    checks = []
    if doc.result_json:
        try:
            checks = json.loads(doc.result_json).get("checks", [])
        except (ValueError, TypeError):
            checks = []
    data = DocumentOut.model_validate(doc).model_dump()
    return DocumentDetail(**data, checks=checks)


@router.post("/{document_id}/recheck", response_model=DocumentOut, status_code=202)
def recheck_document(
    document_id: str,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    doc = _owned_document(document_id, user, db)
    doc.status = ScanStatus.queued
    db.commit()
    db.refresh(doc)

    from app.services.document_runner import process_document

    background.add_task(process_document, doc.id)
    return doc


@router.delete("/{document_id}", status_code=204, response_model=None)
def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    doc = _owned_document(document_id, user, db)
    db.delete(doc)
    db.commit()
