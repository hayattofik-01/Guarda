from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Frequency, Scan, ScanStatus, Target, TargetStatus, User

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OnboardingScanRequest(BaseModel):
    domain: str


class OnboardingScanResponse(BaseModel):
    scan_id: str
    target_id: str


def _normalize_domain(raw: str) -> str:
    d = raw.strip().lower()
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix) :]
    d = d.split("/")[0].split("?")[0]
    if d.startswith("www."):
        d = d[len("www.") :]
    return d.strip()


@router.post("/scan", response_model=OnboardingScanResponse, status_code=201)
def onboarding_scan(
    payload: OnboardingScanRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingScanResponse:
    """Frictionless scan: auto-create + auto-verify the target, then run a scan
    in-process using Guarda's built-in scanners and integrations. No ownership
    proof or API keys are required from the user."""
    domain = _normalize_domain(payload.domain)
    if not domain or "." not in domain:
        raise HTTPException(status_code=400, detail="Enter a valid domain, e.g. acme.com")

    target = db.scalar(
        select(Target).where(Target.owner_id == user.id, Target.address == domain)
    )
    if target is None:
        target = Target(
            owner_id=user.id,
            address=domain,
            status=TargetStatus.verified,
            verified_at=datetime.now(UTC),
            frequency=Frequency.weekly,
            alert_email=user.email,
        )
        db.add(target)
    else:
        # Ensure it's scannable even if it was created earlier in another flow.
        target.status = TargetStatus.verified
        if target.verified_at is None:
            target.verified_at = datetime.now(UTC)
        if not target.alert_email:
            target.alert_email = user.email
    db.commit()
    db.refresh(target)

    scan = Scan(target_id=target.id, status=ScanStatus.queued)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    from app.services.scan_runner import execute_scan

    background.add_task(execute_scan, scan.id)
    return OnboardingScanResponse(scan_id=scan.id, target_id=target.id)
