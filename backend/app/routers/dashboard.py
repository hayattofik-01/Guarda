from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Finding,
    FindingCategory,
    FindingStatus,
    Scan,
    Severity,
    Target,
    TargetStatus,
    User,
)
from app.schemas import DashboardStats
from app.services.scoring import score_from_counts

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DashboardStats:
    target_ids = list(db.scalars(select(Target.id).where(Target.owner_id == user.id)))
    total_targets = len(target_ids)
    verified = db.scalar(
        select(func.count())
        .select_from(Target)
        .where(Target.owner_id == user.id, Target.status == TargetStatus.verified)
    )

    if not target_ids:
        empty = score_from_counts({})
        return DashboardStats(
            targets=0,
            verified_targets=0,
            total_scans=0,
            open_findings=0,
            score=empty["score"],
            grade=empty["grade"],
            score_summary=empty["summary"],
            findings_by_severity={s.value: 0 for s in Severity},
            findings_by_category={c.value: 0 for c in FindingCategory},
        )

    total_scans = db.scalar(
        select(func.count()).select_from(Scan).where(Scan.target_id.in_(target_ids))
    )

    sev_rows = db.execute(
        select(Finding.severity, func.count())
        .join(Scan, Finding.scan_id == Scan.id)
        .where(Scan.target_id.in_(target_ids), Finding.status == FindingStatus.open)
        .group_by(Finding.severity)
    ).all()
    by_sev = {s.value: 0 for s in Severity}
    open_count = 0
    for sev, count in sev_rows:
        by_sev[sev.value] = count
        open_count += count

    cat_rows = db.execute(
        select(Finding.category, func.count())
        .join(Scan, Finding.scan_id == Scan.id)
        .where(Scan.target_id.in_(target_ids), Finding.status == FindingStatus.open)
        .group_by(Finding.category)
    ).all()
    by_cat = {c.value: 0 for c in FindingCategory}
    for cat, count in cat_rows:
        by_cat[cat.value] = count

    score = score_from_counts(by_sev)
    return DashboardStats(
        targets=total_targets,
        verified_targets=verified or 0,
        total_scans=total_scans or 0,
        open_findings=open_count,
        score=score["score"],
        grade=score["grade"],
        score_summary=score["summary"],
        findings_by_severity=by_sev,
        findings_by_category=by_cat,
    )
