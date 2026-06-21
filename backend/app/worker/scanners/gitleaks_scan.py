"""gitleaks — detect leaked secrets in a public Git repository.

Clones a public repo (shallow) and runs gitleaks to find committed API keys,
passwords and tokens. Each leak is a high-severity *sensitive information*
finding.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

from app.config import settings


def available() -> bool:
    return shutil.which("gitleaks") is not None and shutil.which("git") is not None


def _normalize_repo_url(target: str) -> str | None:
    t = target.strip()
    if not t:
        return None
    if t.startswith("http://") or t.startswith("https://"):
        url = t
    elif "/" in t and not t.startswith("git@"):
        url = f"https://github.com/{t}"
    else:
        return None
    if not url.endswith(".git"):
        url = url.rstrip("/") + ".git"
    # Only support repo URLs (must have owner/repo), not bare org pages.
    path = url.replace("https://github.com/", "").replace(".git", "")
    if path.count("/") != 1:
        return None
    return url


def run(github_target: str) -> tuple[list[dict], str]:
    """Return (findings, raw_json)."""
    if not available():
        raise RuntimeError("gitleaks/git is not installed in the worker image")

    repo_url = _normalize_repo_url(github_target)
    if not repo_url:
        raise RuntimeError(
            "github_target must be a public repo as 'owner/repo' or a full repo URL"
        )

    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = os.path.join(tmp, "repo")
        clone = subprocess.run(
            ["git", "clone", "--depth", "50", "--quiet", repo_url, repo_dir],
            capture_output=True,
            text=True,
            timeout=settings.scan_timeout_seconds,
        )
        if clone.returncode != 0:
            raise RuntimeError(f"git clone failed: {clone.stderr.strip()[:300]}")

        report = os.path.join(tmp, "gitleaks.json")
        subprocess.run(
            [
                "gitleaks", "detect",
                "--source", repo_dir,
                "--report-format", "json",
                "--report-path", report,
                "--no-banner",
                "--exit-code", "0",
            ],
            capture_output=True,
            text=True,
            timeout=settings.scan_timeout_seconds,
        )
        raw = ""
        if os.path.exists(report):
            with open(report) as f:
                raw = f.read()
        return _parse(raw, repo_url), raw


def _parse(raw: str, repo_url: str) -> list[dict]:
    if not raw.strip():
        return []
    try:
        leaks = json.loads(raw)
    except json.JSONDecodeError:
        return []
    findings: list[dict] = []
    for leak in leaks:
        rule = leak.get("RuleID") or leak.get("Description") or "secret"
        file = leak.get("File", "")
        line = leak.get("StartLine", "")
        commit = (leak.get("Commit") or "")[:10]
        loc = f"{file}:{line}" if file else repo_url
        findings.append(
            {
                "title": f"Leaked secret in code: {rule}",
                "description": (
                    f"A {rule} appears committed in {repo_url} at {loc} "
                    f"(commit {commit}). Anyone can read this and use it to "
                    "access your systems."
                ),
                "severity": "high",
                "category": "sensitive_info",
                "host": repo_url,
                "source": "gitleaks",
                "location": loc,
                "remediation": (
                    "Immediately rotate/revoke this credential, remove it from "
                    "git history, and store secrets in a secrets manager."
                ),
                "reference": repo_url,
            }
        )
    return findings
