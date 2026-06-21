"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import Shell, { SeverityBadge } from "@/components/Shell";
import { api, Finding, Severity } from "@/lib/api";

const SEVERITIES: (Severity | "")[] = ["", "critical", "high", "medium", "low", "info"];

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [filter, setFilter] = useState<Severity | "">("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(() => {
    api.listFindings(filter || undefined).then(setFindings).catch(() => undefined);
  }, [filter]);

  useEffect(load, [load]);

  async function setStatus(id: string, status: string) {
    await api.updateFinding(id, status);
    load();
  }

  return (
    <Shell>
      <h1 className="page-title">Findings</h1>
      <p className="page-sub">Prioritized by business-risk-aware scoring (CVSS + CISA KEV exploit signal).</p>

      <div className="panel">
        <div className="row" style={{ marginBottom: 14 }}>
          <label style={{ margin: 0 }}>Severity:</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as Severity | "")}
            style={{ width: 180 }}
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s === "" ? "All" : s}
              </option>
            ))}
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Priority</th>
              <th>Severity</th>
              <th>Title</th>
              <th>Host:Port</th>
              <th>CVE</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f) => (
              <Fragment key={f.id}>
                <tr>
                  <td>
                    <strong>{f.priority_score ?? "—"}</strong>
                  </td>
                  <td>
                    <SeverityBadge severity={f.severity} />
                  </td>
                  <td>
                    <a
                      style={{ cursor: "pointer", color: "var(--accent-2)" }}
                      onClick={() => setExpanded(expanded === f.id ? null : f.id)}
                    >
                      {f.title}
                    </a>
                  </td>
                  <td className="muted">
                    {f.host}
                    {f.port ? `:${f.port}` : ""}
                  </td>
                  <td>{f.cve_id || <span className="muted">—</span>}</td>
                  <td>
                    <span className={`badge status-${f.status === "open" ? "queued" : "completed"}`}>
                      {f.status}
                    </span>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {f.status === "open" ? (
                      <>
                        <button
                          className="btn secondary"
                          onClick={() => setStatus(f.id, "fixed")}
                          style={{ marginRight: 6 }}
                        >
                          Mark fixed
                        </button>
                        <button className="btn secondary" onClick={() => setStatus(f.id, "accepted")}>
                          Accept
                        </button>
                      </>
                    ) : (
                      <button className="btn secondary" onClick={() => setStatus(f.id, "open")}>
                        Reopen
                      </button>
                    )}
                  </td>
                </tr>
                {expanded === f.id && (
                  <tr>
                    <td colSpan={7}>
                      <div className="mono">
                        {f.description || "No description."}
                        {f.remediation ? `\n\nRemediation: ${f.remediation}` : ""}
                        {f.cvss_score ? `\n\nCVSS: ${f.cvss_score}` : ""}
                        {f.reference ? `\n\nReferences:\n${f.reference}` : ""}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {findings.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  No findings. Run a scan from a verified target.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
