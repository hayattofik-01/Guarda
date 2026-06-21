from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TargetStatus(str, enum.Enum):
    pending = "pending"          # awaiting ownership verification
    verified = "verified"        # ownership proven, scannable
    failed = "failed"            # verification failed


class VerificationMethod(str, enum.Enum):
    dns_txt = "dns_txt"
    http_file = "http_file"


class ScanStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Severity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Frequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class FindingCategory(str, enum.Enum):
    sensitive_info = "sensitive_info"      # leaked secrets, exposed emails/credentials
    exposed_data = "exposed_data"          # exposed files/dirs/panels/.env/.git
    reputation_risk = "reputation_risk"    # takeover-able assets, leaked info harming brand
    footprint = "footprint"                # discovered assets (subdomains/hosts)


class FindingStatus(str, enum.Enum):
    open = "open"
    fixed = "fixed"
    accepted = "accepted"        # risk accepted / false positive


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    targets: Mapped[list[Target]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    # hostname, IP, or CIDR the user wants to monitor
    address: Mapped[str] = mapped_column(String, index=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[TargetStatus] = mapped_column(Enum(TargetStatus), default=TargetStatus.pending)
    verification_method: Mapped[VerificationMethod] = mapped_column(
        Enum(VerificationMethod), default=VerificationMethod.dns_txt
    )
    verification_token: Mapped[str] = mapped_column(String, default=_uuid)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # how often Guarda re-scans this asset
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency), default=Frequency.weekly)
    # email to alert when sensitive findings are discovered
    alert_email: Mapped[str | None] = mapped_column(String, nullable=True)
    # optional public GitHub org/user or repo URL to scan for leaked secrets
    github_target: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="targets")
    scans: Mapped[list[Scan]] = relationship(back_populates="target", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    target_id: Mapped[str] = mapped_column(ForeignKey("targets.id"), index=True)
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.queued)
    celery_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # raw scanner output for debugging / audit
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    target: Mapped[Target] = relationship(back_populates="scans")
    findings: Mapped[list[Finding]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.info, index=True)
    category: Mapped[FindingCategory] = mapped_column(
        Enum(FindingCategory), default=FindingCategory.exposed_data, index=True
    )
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), default=FindingStatus.open, index=True
    )
    # network context
    host: Mapped[str | None] = mapped_column(String, nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service: Mapped[str | None] = mapped_column(String, nullable=True)
    # source scanner: subfinder | httpx | nuclei | gitleaks | theharvester
    source: Mapped[str] = mapped_column(String, default="nuclei")
    # the discovered evidence/location (URL, file path, host, repo, etc.)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    cve_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # prioritization: blends cvss + exploit intel (e.g. CISA KEV / EPSS / Cala)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan: Mapped[Scan] = relationship(back_populates="findings")
