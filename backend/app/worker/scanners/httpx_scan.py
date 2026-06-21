"""httpx — probe which discovered hosts are live and what they expose.

Takes a list of hosts and returns the live HTTP(S) endpoints with status code,
page title and detected technologies. Live URLs are then handed to nuclei.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from app.config import settings

_RISKY_TITLE_HINTS = ("index of", "login", "phpmyadmin", "dashboard", "admin", "kibana")


def available() -> bool:
    return shutil.which("httpx") is not None


def run(hosts: list[str]) -> tuple[list[dict], str]:
    """Probe hosts. Return (results, raw_jsonl). results = parsed httpx JSON lines."""
    if not available():
        raise RuntimeError("httpx is not installed in the worker image")
    if not hosts:
        return [], ""

    cmd = [
        "httpx",
        "-silent",
        "-json",
        "-title",
        "-tech-detect",
        "-status-code",
        "-no-color",
        "-timeout", "10",
        "-disable-update-check",
    ]
    proc = subprocess.run(
        cmd,
        input="\n".join(hosts),
        capture_output=True,
        text=True,
        timeout=settings.scan_timeout_seconds,
    )
    raw = proc.stdout
    results = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results, raw


def live_urls(results: list[dict]) -> list[str]:
    urls = []
    for r in results:
        url = r.get("url") or r.get("input")
        if url:
            urls.append(url)
    return urls


def to_findings(results: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for r in results:
        url = r.get("url") or r.get("input")
        title = r.get("title") or ""
        status = r.get("status_code") or r.get("status-code")
        tech = r.get("tech") or r.get("technologies") or []
        if isinstance(tech, list):
            tech_str = ", ".join(tech)
        else:
            tech_str = str(tech)

        lowered = title.lower()
        risky = any(h in lowered for h in _RISKY_TITLE_HINTS)
        severity = "medium" if risky else "info"
        category = "exposed_data" if risky else "footprint"

        desc = f"Live endpoint {url}"
        if status:
            desc += f" (HTTP {status})"
        if title:
            desc += f' titled "{title}"'
        if tech_str:
            desc += f"; technologies: {tech_str}"
        if risky:
            desc += (
                ". The page title suggests an admin panel or exposed directory "
                "listing that may not be meant for the public."
            )

        findings.append(
            {
                "title": (f"Exposed page: {title}" if risky and title else f"Live host: {url}"),
                "description": desc,
                "severity": severity,
                "category": category,
                "host": r.get("host") or url,
                "service": tech_str or "http",
                "source": "httpx",
                "location": url,
                "remediation": (
                    "Restrict access to internal tools/admin panels (auth, IP "
                    "allow-listing) and disable public directory listings."
                    if risky
                    else "Confirm this endpoint is meant to be public."
                ),
            }
        )
    return findings
