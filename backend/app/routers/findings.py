from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Finding, Scan, Severity, Target, User
from app.schemas import FindingOut, FindingUpdate

router = APIRouter(prefix="/api/findings", tags=["findings"])


def _user_finding(finding_id: str, user: User, db: Session) -> Finding:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    scan = db.get(Scan, finding.scan_id)
    target = db.get(Target, scan.target_id) if scan else None
    if target is None or target.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.get("", response_model=list[FindingOut])
def list_findings(
    severity: Severity | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Finding]:
    stmt = (
        select(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(Target, Scan.target_id == Target.id)
        .where(Target.owner_id == user.id)
        .order_by(Finding.priority_score.desc().nullslast())
    )
    if severity is not None:
        stmt = stmt.where(Finding.severity == severity)
    return list(db.scalars(stmt))


@router.patch("/{finding_id}", response_model=FindingOut)
def update_finding(
    finding_id: str,
    payload: FindingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Finding:
    finding = _user_finding(finding_id, user, db)
    finding.status = payload.status
    db.commit()
    db.refresh(finding)
    return finding
