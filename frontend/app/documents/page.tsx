"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import Shell from "@/components/Shell";
import { api, ApiError, GuardaDocument, GuardaDocumentDetail } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  compliant: "Compliant",
  gaps: "Gaps found",
  non_compliant: "Non-compliant",
};

function complianceClass(status: string | null): string {
  if (status === "compliant") return "check-pass";
  if (status === "gaps") return "sev-medium";
  return "check-fail";
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<GuardaDocument[]>([]);
  const [detail, setDetail] = useState<GuardaDocumentDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  function load() {
    api
      .listDocuments()
      .then(setDocs)
      .catch(() => undefined);
  }
  useEffect(load, []);

  // Auto-refresh while any document is still being checked.
  useEffect(() => {
    if (!docs.some((d) => d.status === "queued" || d.status === "running")) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [docs]);

  async function onUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setBusy(true);
    try {
      await api.uploadDocument(file);
      if (fileRef.current) fileRef.current.value = "";
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRecheck(id: string) {
    await api.recheckDocument(id);
    load();
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this document and its compliance history?")) return;
    if (detail?.id === id) setDetail(null);
    await api.deleteDocument(id);
    load();
  }

  async function openDetail(id: string) {
    setDetail(null);
    try {
      setDetail(await api.getDocument(id));
    } catch {
      setError("Could not load that document.");
    }
  }

  return (
    <Shell>
      <h1 className="page-title">Documents &amp; contracts</h1>
      <p className="page-sub">
        Drop in the policies and contracts you already have — DPAs, privacy
        policies, vendor agreements. Guarda reads them and checks them against the
        key GDPR articles automatically, then re-checks them on your schedule and
        emails you if anything is missing. No setup, no choosing what to verify.
      </p>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Upload a document</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          PDF, Word (.docx) or plain text. We extract the text and run a GDPR
          compliance check the moment it lands.
        </p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt,.md,application/pdf,text/plain"
          onChange={onUpload}
          disabled={busy}
        />
        {busy && <span className="muted" style={{ marginLeft: 10 }}>Uploading…</span>}
        {error && <div className="error">{error}</div>}
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Document</th>
              <th>Status</th>
              <th>Compliance</th>
              <th>Score</th>
              <th>Next check</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>
                  <button
                    onClick={() => openDetail(d.id)}
                    style={{
                      color: "var(--accent-2)",
                      background: "none",
                      border: "none",
                      padding: 0,
                      cursor: "pointer",
                      font: "inherit",
                      textAlign: "left",
                    }}
                  >
                    {d.filename}
                  </button>
                </td>
                <td style={{ textTransform: "capitalize" }}>{d.status}</td>
                <td>
                  {d.compliance_status ? (
                    <span className={`badge ${complianceClass(d.compliance_status)}`}>
                      {STATUS_LABEL[d.compliance_status] || d.compliance_status}
                    </span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>
                  {d.compliance_score != null ? (
                    `${d.compliance_score}/100`
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>
                  {d.next_check_at ? (
                    new Date(d.next_check_at).toLocaleDateString()
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn secondary" onClick={() => onRecheck(d.id)}>
                    Re-check
                  </button>{" "}
                  <button className="btn danger" onClick={() => onDelete(d.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No documents yet. Upload a contract or policy above and we&apos;ll
                  check it for you.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="panel compliance">
          <div className="flex-between" style={{ alignItems: "flex-start" }}>
            <h3 style={{ marginTop: 0 }}>{detail.filename}</h3>
            <span className={`badge ${complianceClass(detail.compliance_status)}`}>
              {detail.compliance_status
                ? STATUS_LABEL[detail.compliance_status] || detail.compliance_status
                : detail.status}
            </span>
          </div>
          {detail.summary && (
            <p className="muted" style={{ marginTop: 0 }}>{detail.summary}</p>
          )}
          {detail.checks.length > 0 && (
            <ul>
              {detail.checks.map((c, i) => (
                <li key={i}>
                  <span className={`check-mark ${c.passed ? "check-pass" : "check-fail"}`}>
                    {c.passed ? "\u2713" : "\u2717"}
                  </span>
                  <div>
                    <div>
                      {c.requirement}{" "}
                      <span className="gdpr-article">{c.article}</span>
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>{c.detail}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {detail.advice && (
            <div style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.6 }}>
              {detail.advice}
            </div>
          )}
        </div>
      )}
    </Shell>
  );
}
