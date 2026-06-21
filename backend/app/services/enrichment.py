"""Finding enrichment & prioritization.

Prioritization blends technical severity (CVSS) with real-world exploitation
signal. We pull the CISA Known-Exploited-Vulnerabilities (KEV) catalog (free, no
key) and optionally enrich via Cala.ai when a key is configured.

priority_score (0-100) = base CVSS*10 weighted up when the CVE is known to be
actively exploited.
"""

from __future__ import annotations

import time

import httpx

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

_kev_cache: dict[str, object] = {"fetched_at": 0.0, "cves": set()}
_KEV_TTL = 60 * 60 * 6  # 6 hours


def _load_kev() -> set[str]:
    now = time.time()
    if now - float(_kev_cache["fetched_at"]) < _KEV_TTL and _kev_cache["cves"]:
        return _kev_cache["cves"]  # type: ignore[return-value]
    try:
        resp = httpx.get(CISA_KEV_URL, timeout=20)
        resp.raise_for_status()
        cves = {item["cveID"] for item in resp.json().get("vulnerabilities", [])}
        _kev_cache["cves"] = cves
        _kev_cache["fetched_at"] = now
        return cves
    except Exception:
        # On failure, fall back to whatever we have cached (possibly empty).
        return _kev_cache["cves"]  # type: ignore[return-value]


def is_known_exploited(cve_id: str | None) -> bool:
    if not cve_id:
        return False
    return cve_id.upper() in _load_kev()


def compute_priority(severity: str, cvss_score: float | None, cve_id: str | None) -> float:
    """Return a 0-100 priority score."""
    severity_base = {
        "info": 5,
        "low": 25,
        "medium": 50,
        "high": 75,
        "critical": 90,
    }
    base = (cvss_score * 10) if cvss_score else severity_base.get(severity, 25)
    if is_known_exploited(cve_id):
        base = min(100.0, base * 1.25 + 10)
    return round(min(base, 100.0), 1)
