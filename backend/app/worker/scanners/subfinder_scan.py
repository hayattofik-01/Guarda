"""subfinder — passive subdomain discovery.

Maps an organization's public footprint by enumerating subdomains from many
free passive sources. Output is one subdomain per line.
"""

from __future__ import annotations

import shutil
import subprocess

from app.config import settings


def available() -> bool:
    return shutil.which("subfinder") is not None


def run(domain: str) -> tuple[list[str], str]:
    """Return (subdomains, raw_output)."""
    if not available():
        raise RuntimeError("subfinder is not installed in the worker image")

    cmd = [
        "subfinder",
        "-d", domain,
        "-silent",
        "-timeout", "15",
        "-max-time", str(settings.subfinder_max_time // 60 or 1),
        "-disable-update-check",
    ]
    if settings.subfinder_use_all_sources:
        cmd.append("-all")
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=settings.subfinder_max_time + 30,
    )
    raw = proc.stdout
    subs = sorted({line.strip() for line in raw.splitlines() if line.strip()})
    return subs, raw


def to_findings(subdomains: list[str], root: str) -> list[dict]:
    findings: list[dict] = []
    for sub in subdomains:
        if sub == root:
            continue
        findings.append(
            {
                "title": f"Subdomain discovered: {sub}",
                "description": (
                    f"{sub} is publicly discoverable and part of your internet "
                    "footprint. Every exposed subdomain widens your attack surface."
                ),
                "severity": "info",
                "category": "footprint",
                "host": sub,
                "source": "subfinder",
                "location": sub,
                "remediation": (
                    "Confirm this host should be public. Decommission unused or "
                    "forgotten subdomains."
                ),
            }
        )
    return findings
