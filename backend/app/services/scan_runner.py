"""In-process scan execution (no Celery/worker required).

The free deploy has no Celery worker or Redis broker, so scans run directly in
the API process via FastAPI background tasks. The Celery task in
``app.worker.tasks`` is a thin wrapper around :func:`execute_scan` for the
worker-based deployment.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.database import SessionLocal
from app.models import (
    Finding,
    FindingCategory,
    Scan,
    ScanStatus,
    Severity,
    Target,
)
from app.services.advice_agent import start_advice
from app.services.enrichment import compute_priority, is_known_exploited
from app.services.gdpr import gdpr_assessment
from app.services.scheduling import next_run
from app.worker.scanners import (
    gitleaks_scan,
    httpx_scan,
    nuclei_scan,
    subfinder_scan,
    theharvester_scan,
)

# Findings in these categories (or at/above high severity) trigger an alert.
_ALERT_CATEGORIES = {FindingCategory.sensitive_info, FindingCategory.reputation_risk}
_ALERT_SEVERITIES = {Severity.high, Severity.critical}


def _run_footprint_pipeline(target: Target) -> tuple[list[dict], list[str], list[str]]:
    """Run the OSINT pipeline. Return (findings, raw_chunks, errors)."""
    findings: list[dict] = []
    raw_chunks: list[str] = []
    errors: list[str] = []
    domain = target.address

    # 1. Passive subdomain discovery.
    subdomains: list[str] = []
    if subfinder_scan.available():
        try:
            subdomains, raw = subfinder_scan.run(domain)
            findings.extend(subfinder_scan.to_findings(subdomains, domain))
            raw_chunks.append(f"### subfinder\n{raw}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"subfinder: {exc}")
    else:
        errors.append("subfinder: not installed, skipped")

    # 2. Probe which hosts are live (include the root domain).
    hosts = sorted({domain, *subdomains})
    live_urls: list[str] = []
    if httpx_scan.available():
        try:
            results, raw = httpx_scan.run(hosts)
            findings.extend(httpx_scan.to_findings(results))
            live_urls = httpx_scan.live_urls(results)
            raw_chunks.append(f"### httpx\n{raw}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"httpx: {exc}")
    else:
        errors.append("httpx: not installed, skipped")
        live_urls = [domain]

    # 3. Exposure/misconfiguration checks on live endpoints.
    if nuclei_scan.available():
        try:
            nf, raw = nuclei_scan.run(live_urls or [domain])
            findings.extend(nf)
            raw_chunks.append(f"### nuclei\n{raw}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"nuclei: {exc}")
    else:
        errors.append("nuclei: not installed, skipped")

    # 4. Leaked secrets in public source code (optional, when a repo is provided).
    if target.github_target:
        if gitleaks_scan.available():
            try:
                gf, raw = gitleaks_scan.run(target.github_target)
                findings.extend(gf)
                raw_chunks.append(f"### gitleaks\n{raw[:50_000]}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"gitleaks: {exc}")
        else:
            errors.append("gitleaks: not installed, skipped")

    # 5. Leaked emails/hosts from public OSINT sources (best-effort).
    if theharvester_scan.available():
        try:
            hf, raw = theharvester_scan.run(domain)
            findings.extend(hf)
            raw_chunks.append(f"### theharvester\n{raw[:50_000]}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"theharvester: {exc}")

    return findings, raw_chunks, errors


def execute_scan(scan_id: str) -> str:
    """Run a scan end-to-end and persist findings. Safe to call in-process."""
    db = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        if scan is None:
            return "scan-not-found"
        target = db.get(Target, scan.target_id)
        if target is None:
            scan.status = ScanStatus.failed
            scan.error = "Target not found"
            db.commit()
            return "target-not-found"

        scan.status = ScanStatus.running
        scan.started_at = datetime.now(UTC)
        db.commit()

        all_findings, raw_chunks, errors = _run_footprint_pipeline(target)

        stored: list[Finding] = []
        for data in all_findings:
            severity = Severity(data.get("severity", "info"))
            category = FindingCategory(data.get("category", "exposed_data"))
            cve_id = data.get("cve_id")
            cvss = data.get("cvss_score")
            priority = compute_priority(severity.value, cvss, cve_id)
            description = data.get("description")
            if is_known_exploited(cve_id):
                kev_note = "[KEV] Actively exploited per CISA Known-Exploited-Vulnerabilities."
                description = f"{kev_note} {description or ''}".strip()
            finding = Finding(
                scan_id=scan.id,
                title=data["title"],
                description=description,
                severity=severity,
                category=category,
                host=data.get("host"),
                port=data.get("port"),
                service=data.get("service"),
                source=data.get("source", "nuclei"),
                location=data.get("location"),
                cve_id=cve_id,
                cvss_score=cvss,
                priority_score=priority,
                remediation=data.get("remediation"),
                reference=data.get("reference"),
            )
            db.add(finding)
            stored.append(finding)

        scan.raw_output = "\n\n".join(raw_chunks)[:500_000]
        scan.finished_at = datetime.now(UTC)
        # A scan is "completed" if at least one scanner ran; only fully-failed runs fail.
        ran_any = len(raw_chunks) > 0
        scan.status = ScanStatus.completed if ran_any else ScanStatus.failed
        if errors:
            scan.error = "; ".join(errors)

        # Schedule the next automated run for this asset.
        now = datetime.now(UTC)
        target.last_scan_at = now
        target.next_scan_at = next_run(target.frequency, after=now)

        # Generate remediation advice (deterministic now; Devin upgrade if configured).
        try:
            gdpr = gdpr_assessment(target.address, stored, scan_id=scan.id)
            start_advice(scan, target.address, stored, gdpr.get("summary"))
        except Exception:  # noqa: BLE001 - advice is best-effort
            pass

        db.commit()

        _alert_if_sensitive(db, target, scan, stored)
        return scan.status.value
    finally:
        db.close()


def _alert_if_sensitive(db, target: Target, scan: Scan, findings: list[Finding]) -> None:
    """Alert the user (email + WhatsApp) when sensitive findings are discovered."""
    if not (target.alert_email or target.alert_whatsapp):
        return
    flagged = [
        f
        for f in findings
        if f.category in _ALERT_CATEGORIES or f.severity in _ALERT_SEVERITIES
    ]
    if not flagged:
        return
    from app.services.notifications import send_sensitive_alert
    from app.services.report import build_report

    try:
        report = build_report(target, scan, findings)
        send_sensitive_alert(
            target.address,
            flagged,
            report,
            scan.id,
            email=target.alert_email,
            whatsapp=target.alert_whatsapp,
        )
    except Exception:  # noqa: BLE001 - alerts are best-effort
        pass
