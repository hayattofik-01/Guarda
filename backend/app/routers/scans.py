from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Scan, ScanStatus, Target, TargetStatus, User
from app.schemas import ScanDetail, ScanOut

router = APIRouter(prefix="/api/scans", tags=["scans"])


def _owned_scan(scan_id: str, user: User, db: Session) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    target = db.get(Target, scan.target_id)
    if target is None or target.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/targets/{target_id}", response_model=ScanOut, status_code=201)
def start_scan(
    target_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scan:
    target = db.get(Target, target_id)
    if target is None or target.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Target not found")
    if target.status != TargetStatus.verified:
        raise HTTPException(
            status_code=403,
            detail="Target ownership not verified. Verify before scanning.",
        )

    scan = Scan(target_id=target.id, status=ScanStatus.queued)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Import here to avoid a hard dependency on the worker package at API import time.
    from app.worker.tasks import run_scan

    async_result = run_scan.delay(scan.id)
    scan.celery_task_id = async_result.id
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/targets/{target_id}", response_model=list[ScanOut])
def list_scans_for_target(
    target_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Scan]:
    target = db.get(Target, target_id)
    if target is None or target.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Target not found")
    return list(
        db.scalars(
            select(Scan).where(Scan.target_id == target_id).order_by(Scan.created_at.desc())
        )
    )


@router.get("/{scan_id}", response_model=ScanDetail)
def get_scan(
    scan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scan:
    return _owned_scan(scan_id, user, db)
