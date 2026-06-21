"""theHarvester — passive OSINT for leaked emails and hosts.

Gathers emails and hostnames associated with a domain from free public
sources. Exposed corporate emails fuel phishing and credential-stuffing, so
they are surfaced as sensitive-information findings.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

from app.config import settings

# Keyless, generally-reliable sources.
_SOURCES = "crtsh,duckduckgo,bing,otx,rapiddns,hackertarget"


def available() -> bool:
    return shutil.which("theHarvester") is not None


def run(domain: str) -> tuple[list[dict], str]:
    """Return (findings, raw_json)."""
    if not available():
        raise RuntimeError("theHarvester is not installed in the worker image")

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "harvest")
        # Bound runtime; on timeout keep whatever was written to the output file.
        try:
            subprocess.run(
                ["theHarvester", "-d", domain, "-b", _SOURCES, "-f", out],
                capture_output=True,
                text=True,
                timeout=settings.harvester_deadline_seconds,
            )
        except subprocess.TimeoutExpired:
            pass
        raw = ""
        path = out if os.path.exists(out) else f"{out}.json"
        if os.path.exists(path):
            with open(path) as f:
                raw = f.read()
        return _parse(raw, domain), raw


def _parse(raw: str, domain: str) -> list[dict]:
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    findings: list[dict] = []
    emails = data.get("emails") or []
    for email in emails:
        findings.append(
            {
                "title": f"Exposed email address: {email}",
                "description": (
                    f"{email} was found in public sources tied to {domain}. "
                    "Publicly exposed corporate emails are prime targets for "
                    "phishing and credential-stuffing attacks."
                ),
                "severity": "low",
                "category": "sensitive_info",
                "host": domain,
                "source": "theharvester",
                "location": email,
                "remediation": (
                    "Enforce MFA on accounts, train staff on phishing, and avoid "
                    "publishing individual addresses where possible."
                ),
            }
        )

    hosts = data.get("hosts") or []
    for host in hosts:
        name = host.split(":")[0] if isinstance(host, str) else str(host)
        findings.append(
            {
                "title": f"Public host discovered: {name}",
                "description": f"{name} is publicly associated with {domain}.",
                "severity": "info",
                "category": "footprint",
                "host": name,
                "source": "theharvester",
                "location": name,
                "remediation": "Confirm this host is intended to be public.",
            }
        )
    return findings
