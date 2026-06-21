from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import (
    FindingCategory,
    FindingStatus,
    Frequency,
    ScanStatus,
    Severity,
    TargetStatus,
    VerificationMethod,
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    created_at: datetime


class TargetCreate(BaseModel):
    address: str
    label: str | None = None
    verification_method: VerificationMethod = VerificationMethod.dns_txt
    frequency: Frequency = Frequency.weekly
    alert_email: EmailStr | None = None
    alert_whatsapp: str | None = None
    github_target: str | None = None


class TargetUpdate(BaseModel):
    label: str | None = None
    frequency: Frequency | None = None
    alert_email: EmailStr | None = None
    alert_whatsapp: str | None = None
    github_target: str | None = None


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    address: str
    label: str | None
    status: TargetStatus
    verification_method: VerificationMethod
    verification_token: str
    verified_at: datetime | None
    frequency: Frequency
    alert_email: str | None
    alert_whatsapp: str | None
    github_target: str | None
    created_at: datetime


class VerificationInstructions(BaseModel):
    method: VerificationMethod
    token: str
    instructions: str


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    scan_id: str
    title: str
    description: str | None
    severity: Severity
    category: FindingCategory
    status: FindingStatus
    host: str | None
    port: int | None
    service: str | None
    source: str
    location: str | None
    cve_id: str | None
    cvss_score: float | None
    priority_score: float | None
    remediation: str | None
    reference: str | None
    created_at: datetime


class FindingUpdate(BaseModel):
    status: FindingStatus


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    target_id: str
    status: ScanStatus
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    created_at: datetime


class ScanDetail(ScanOut):
    findings: list[FindingOut] = []


class DashboardStats(BaseModel):
    targets: int
    verified_targets: int
    total_scans: int
    open_findings: int
    score: int
    grade: str
    score_summary: str
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]


class Report(BaseModel):
    asset: str
    label: str | None
    generated_at: str
    scan_id: str
    overall_risk: str
    score: int
    grade: str
    score_summary: str
    compliance: list[dict[str, Any]]
    headline: str
    totals: dict[str, Any]
    next_steps: list[str]
    sections: list[dict[str, Any]]
