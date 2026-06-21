"""nuclei templated vulnerability scanner.

Runs nuclei with JSONL output and normalizes each result into a finding dict.
nuclei provides CVE checks, misconfigurations, exposures, and more via its
community template library.
"""

from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess

from app.config import settings

_SEVERITY_MAP = {
    "info": "info",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
    "unknown": "info",
}


def available() -> bool:
    return shutil.which("nuclei") is not None


def _as_url(address: str) -> str:
    try:
        ipaddress.ip_network(address, strict=False)
        return address  # bare IP/CIDR; let nuclei handle scheme probing
    except ValueError:
        return address  # hostname; nuclei will probe http/https


def run(address: str) -> tuple[list[dict], str]:
    """Return (findings, raw_jsonl)."""
    if not available():
        raise RuntimeError("nuclei is not installed in the worker image")

    cmd = [
        "nuclei",
        "-target", _as_url(address),
        "-severity", settings.nuclei_severity,
        "-jsonl",
        "-silent",
        "-no-color",
        "-disable-update-check",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=settings.scan_timeout_seconds,
    )
    raw = proc.stdout
    return _parse(raw), raw


def _parse(jsonl: str) -> list[dict]:
    findings: list[dict] = []
    for line in jsonl.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        info = item.get("info", {})
        severity = _SEVERITY_MAP.get((info.get("severity") or "info").lower(), "info")
        classification = info.get("classification") or {}
        cve_ids = classification.get("cve-id") or []
        cve_id = cve_ids[0] if isinstance(cve_ids, list) and cve_ids else None
        cvss = classification.get("cvss-score")

        refs = info.get("reference") or []
        reference = "\n".join(refs) if isinstance(refs, list) else str(refs)

        findings.append(
            {
                "title": info.get("name") or item.get("template-id", "nuclei finding"),
                "description": info.get("description"),
                "severity": severity,
                "host": item.get("host") or item.get("matched-at"),
                "port": item.get("port"),
                "service": item.get("type"),
                "source": "nuclei",
                "cve_id": cve_id,
                "cvss_score": float(cvss) if cvss else None,
                "remediation": info.get("remediation"),
                "reference": reference or item.get("matched-at"),
            }
        )
    return findings
