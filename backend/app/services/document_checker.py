"""GDPR compliance checking for uploaded contracts / policies.

Guarda extracts the text of an uploaded document and checks it for the GDPR
clauses an enterprise data-protection reviewer expects to see (DPA, lawful
basis, data-subject rights, breach notification, international transfers, etc.).
The verdict is deterministic so it never fails, and is enriched with Cala's
verified organisation intelligence for the account's domain when available.
"""

from __future__ import annotations

import io
import json
import logging

logger = logging.getLogger(__name__)


# Each clause: (id, GDPR article, human label, keyword signals).
_CLAUSES: list[tuple[str, str, str, tuple[str, ...]]] = [
    (
        "lawful_basis",
        "Art. 6",
        "Lawful basis for processing is stated",
        ("lawful basis", "legitimate interest", "consent", "legal basis", "article 6"),
    ),
    (
        "data_subject_rights",
        "Art. 12-23",
        "Data-subject rights are described (access, erasure, portability)",
        ("right to access", "right to erasure", "data subject rights", "right to be forgotten",
         "data portability", "rectification"),
    ),
    (
        "processor_dpa",
        "Art. 28",
        "Processor / Data Processing Agreement obligations are present",
        ("data processing agreement", "data processor", "sub-processor", "subprocessor",
         "processing on behalf", "article 28"),
    ),
    (
        "security_measures",
        "Art. 32",
        "Technical & organisational security measures are committed",
        ("security measures", "encryption", "technical and organisational",
         "technical and organizational", "pseudonymisation", "confidentiality"),
    ),
    (
        "breach_notification",
        "Art. 33-34",
        "Personal-data breach notification process is defined",
        ("breach notification", "data breach", "notify", "72 hours", "personal data breach"),
    ),
    (
        "international_transfers",
        "Art. 44-49",
        "International data-transfer safeguards are addressed",
        ("standard contractual clauses", "international transfer", "scc", "data transfer",
         "adequacy decision", "third country"),
    ),
    (
        "retention",
        "Art. 5(1)(e)",
        "Data retention / minimisation is specified",
        ("retention period", "data retention", "data minimisation", "data minimization",
         "no longer than", "storage limitation"),
    ),
    (
        "dpo_contact",
        "Art. 37-39",
        "A data-protection contact / DPO is identified",
        ("data protection officer", "dpo", "data protection contact", "privacy officer"),
    ),
]


def extract_text(filename: str, raw: bytes) -> str:
    """Best-effort plain-text extraction from PDF / DOCX / text uploads."""
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if name.endswith(".docx"):
            from docx import Document as Docx

            doc = Docx(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:  # noqa: BLE001 - fall through to raw decode
        logger.warning("Document extraction failed for %s: %s", filename, exc)
    # Plain text / fallback.
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def check_text(text: str) -> dict:
    """Run the deterministic GDPR clause checklist over the document text."""
    haystack = (text or "").lower()
    checks = []
    present = 0
    for _cid, article, label, signals in _CLAUSES:
        found = any(sig in haystack for sig in signals)
        if found:
            present += 1
        checks.append(
            {
                "article": article,
                "requirement": label,
                "passed": found,
                "detail": (
                    "Clause language detected in the document."
                    if found
                    else "No matching clause language found — add or clarify this."
                ),
            }
        )

    total = len(_CLAUSES)
    score = round(100 * present / total) if total else 0
    if not haystack.strip():
        status = "non_compliant"
        summary = (
            "We couldn't read any text from this document. Upload a text-based "
            "PDF/DOCX (not a scan/image) so Guarda can assess it."
        )
    elif score >= 80:
        status = "compliant"
        summary = (
            f"Strong GDPR coverage — {present}/{total} key clauses present. "
            "Review any gaps below before an enterprise data-protection review."
        )
    elif score >= 50:
        status = "gaps"
        summary = (
            f"Partial GDPR coverage — {present}/{total} key clauses present. "
            "Close the missing clauses below to pass a buyer's review."
        )
    else:
        status = "non_compliant"
        summary = (
            f"Significant GDPR gaps — only {present}/{total} key clauses present. "
            "This document likely won't pass an enterprise data-protection review."
        )
    return {
        "score": score,
        "status": status,
        "summary": summary,
        "checks": checks,
        "present": present,
        "total": total,
    }


def document_advice(result: dict) -> str:
    """Deterministic, actionable advice from a document check result."""
    failed = [c for c in result.get("checks", []) if not c["passed"]]
    if not failed:
        return (
            "This document covers the core GDPR clauses an enterprise buyer looks "
            "for. Keep it versioned and re-check it whenever you change vendors or "
            "data flows."
        )
    lines = ["Add or strengthen these clauses to close your GDPR gaps:"]
    for c in failed:
        lines.append(f"- **{c['requirement']}** ({c['article']})")
    return "\n".join(lines)


def run_document_check(filename: str, content_text: str) -> dict:
    """Full document check pipeline. Returns a serialisable result dict."""
    result = check_text(content_text)
    result["advice"] = document_advice(result)
    result["result_json"] = json.dumps({"checks": result["checks"]})
    return result
