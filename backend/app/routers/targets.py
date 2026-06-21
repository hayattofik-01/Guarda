from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Target, TargetStatus, User, VerificationMethod
from app.schemas import (
    TargetCreate,
    TargetOut,
    VerificationInstructions,
)
from app.services import ownership

router = APIRouter(prefix="/api/targets", tags=["targets"])


def _get_owned_target(target_id: str, user: User, db: Session) -> Target:
    target = db.get(Target, target_id)
    if target is None or target.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.get("", response_model=list[TargetOut])
def list_targets(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Target]:
    return list(db.scalars(select(Target).where(Target.owner_id == user.id)))


@router.post("", response_model=TargetOut, status_code=201)
def create_target(
    payload: TargetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Target:
    target = Target(
        owner_id=user.id,
        address=payload.address.strip().lower(),
        label=payload.label,
        verification_method=payload.verification_method,
        schedule=payload.schedule,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/{target_id}", response_model=TargetOut)
def get_target(
    target_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Target:
    return _get_owned_target(target_id, user, db)


@router.get("/{target_id}/verification", response_model=VerificationInstructions)
def verification_instructions(
    target_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerificationInstructions:
    target = _get_owned_target(target_id, user, db)
    if target.verification_method == VerificationMethod.dns_txt:
        text = ownership.dns_instructions(target.address, target.verification_token)
    else:
        text = ownership.http_instructions(target.address, target.verification_token)
    return VerificationInstructions(
        method=target.verification_method,
        token=target.verification_token,
        instructions=text,
    )


@router.post("/{target_id}/verify", response_model=TargetOut)
def verify_target(
    target_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Target:
    target = _get_owned_target(target_id, user, db)
    if target.verification_method == VerificationMethod.dns_txt:
        ok = ownership.verify_dns_txt(target.address, target.verification_token)
    else:
        ok = ownership.verify_http_file(target.address, target.verification_token)

    if ok:
        target.status = TargetStatus.verified
        target.verified_at = datetime.now(UTC)
    else:
        target.status = TargetStatus.failed
    db.commit()
    db.refresh(target)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Verification token not found. Add the record/file and retry.",
        )
    return target


@router.delete("/{target_id}", status_code=204)
def delete_target(
    target_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    target = _get_owned_target(target_id, user, db)
    db.delete(target)
    db.commit()
