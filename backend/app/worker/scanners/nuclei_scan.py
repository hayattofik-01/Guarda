"""nuclei exposure/misconfiguration scanner.

Guarda runs nuclei with exposure-focused tags to surface *exposed data*:
open directories, exposed `.env`/`.git`, config/backup files, log files,
leaked tokens, and subdomain-takeover risks. Each result is normalized into a
finding dict and classified into a Guarda category.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

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


def _classify(tags: list[str], template_id: str) -> str:
    joined = " ".join(tags + [template_id]).lower()
    if any(t in joined for t in ("secret", "token", "credential", "apikey", "api-key")):
        return "sensitive_info"
    if any(t in joined for t in ("takeover", "subdomain-takeover")):
        return "reputation_risk"
    return "exposed_data"


def run(targets: list[str] | str) -> tuple[list[dict], str]:
    """Run nuclei against one or many hosts/URLs. Return (findings, raw_jsonl)."""
    if not available():
        raise RuntimeError("nuclei is not installed in the worker image")
    if isinstance(targets, str):
        targets = [targets]
    targets = [t for t in targets if t]
    if not targets:
        return [], ""

    # Bound the workload so onboarding scans stay fast on small instances.
    targets = targets[: settings.nuclei_max_targets]

    with tempfile.TemporaryDirectory() as tmp:
        list_file = os.path.join(tmp, "targets.txt")
        with open(list_file, "w") as f:
            f.write("\n".join(targets))
        cmd = [
            "nuclei",
            "-l", list_file,
            "-tags", settings.nuclei_tags,
            "-severity", settings.nuclei_severity,
            "-concurrency", str(settings.nuclei_concurrency),
            "-rate-limit", str(settings.nuclei_rate_limit),
            "-timeout", str(settings.nuclei_request_timeout),
            "-retries", "1",
            "-no-interactsh",
            "-jsonl",
            "-silent",
            "-no-color",
            "-disable-update-check",
        ]
        # Use Popen so a deadline hit still keeps whatever findings nuclei has
        # already streamed to stdout (subprocess.run would discard them).
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        try:
            raw, _ = proc.communicate(timeout=settings.nuclei_deadline_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            raw, _ = proc.communicate()
        return _parse(raw or ""), (raw or "")


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
        tags = info.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        template_id = item.get("template-id", "")
        category = _classify(tags, template_id)

        classification = info.get("classification") or {}
        cve_ids = classification.get("cve-id") or []
        cve_id = cve_ids[0] if isinstance(cve_ids, list) and cve_ids else None
        cvss = classification.get("cvss-score")

        refs = info.get("reference") or []
        reference = "\n".join(refs) if isinstance(refs, list) else str(refs)
        matched = item.get("matched-at") or item.get("host")

        findings.append(
            {
                "title": info.get("name") or template_id or "nuclei finding",
                "description": info.get("description"),
                "severity": severity,
                "category": category,
                "host": item.get("host") or matched,
                "port": item.get("port"),
                "service": item.get("type"),
                "source": "nuclei",
                "location": matched,
                "cve_id": cve_id,
                "cvss_score": float(cvss) if cvss else None,
                "remediation": info.get("remediation"),
                "reference": reference or matched,
            }
        )
    return findings
