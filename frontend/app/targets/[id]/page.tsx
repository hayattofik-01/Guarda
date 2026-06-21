"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Shell, { CategoryBadge, SeverityBadge, StatusBadge } from "@/components/Shell";
import {
  api,
  ApiError,
  Finding,
  Scan,
  Target,
  VerificationInstructions,
} from "@/lib/api";

export default function TargetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [target, setTarget] = useState<Target | null>(null);
  const [instr, setInstr] = useState<VerificationInstructions | null>(null);
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedScan, setSelectedScan] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const loadScans = useCallback(() => {
    api.listScans(id).then(setScans).catch(() => undefined);
  }, [id]);

  const load = useCallback(() => {
    api.getTarget(id).then(setTarget).catch(() => undefined);
    api.verification(id).then(setInstr).catch(() => undefined);
    loadScans();
  }, [id, loadScans]);

  useEffect(load, [load]);

  // Poll scans while any are running/queued.
  useEffect(() => {
    const active = scans.some((s) => s.status === "running" || s.status === "queued");
    if (!active) return;
    const t = setInterval(loadScans, 4000);
    return () => clearInterval(t);
  }, [scans, loadScans]);

  async function onVerify() {
    setError("");
    setMsg("");
    try {
      const t = await api.verifyTarget(id);
      setTarget(t);
      setMsg("Ownership verified.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verification failed");
    }
  }

  async function onScan() {
    setError("");
    try {
      await api.startScan(id);
      setMsg("Scan queued.");
      loadScans();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start scan");
    }
  }

  async function openScan(scanId: string) {
    setSelectedScan(scanId);
    const detail = await api.getScan(scanId);
    setFindings(detail.findings);
  }

  if (!target) {
    return (
      <Shell>
        <p className="muted">Loading…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="flex-between">
        <div>
          <h1 className="page-title">{target.address}</h1>
          <p className="page-sub">
            <StatusBadge status={target.status} />{" "}
            {target.label && <span className="muted">· {target.label}</span>}
          </p>
        </div>
        <button className="btn secondary" onClick={() => router.push("/targets")}>
          ← Assets
        </button>
      </div>

      {msg && <div className="panel" style={{ color: "var(--green)" }}>{msg}</div>}
      {error && <div className="panel error">{error}</div>}

      {target.status !== "verified" && instr && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Verify ownership</h3>
          <p className="muted">
            Prove you control this asset before scanning. Method:{" "}
            <strong>{instr.method === "dns_txt" ? "DNS TXT" : "HTTP file"}</strong>
          </p>
          <div className="mono">{instr.instructions}</div>
          <div style={{ marginTop: 14 }}>
            <button className="btn" onClick={onVerify}>
              Verify now
            </button>
          </div>
        </div>
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Monitoring settings</h3>
        <div className="row" style={{ gap: 32, flexWrap: "wrap" }}>
          <div>
            <div className="label">Scan frequency</div>
            <div style={{ textTransform: "capitalize" }}>{target.frequency}</div>
          </div>
          <div>
            <div className="label">Alert email</div>
            <div>{target.alert_email || <span className="muted">not set</span>}</div>
          </div>
          <div>
            <div className="label">WhatsApp alert</div>
            <div>{target.alert_whatsapp || <span className="muted">not set</span>}</div>
          </div>
          <div>
            <div className="label">GitHub repo</div>
            <div>{target.github_target || <span className="muted">none</span>}</div>
          </div>
        </div>
      </div>

      {target.status === "verified" && (
        <div className="panel">
          <div className="flex-between">
            <div>
              <h3 style={{ margin: 0 }}>Scans</h3>
              <span className="muted">Run an on-demand scan or rely on the schedule.</span>
            </div>
            <button className="btn" onClick={onScan}>
              Run scan now
            </button>
          </div>
          <table style={{ marginTop: 14 }}>
            <thead>
              <tr>
                <th>Started</th>
                <th>Status</th>
                <th>Finished</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {scans.map((s) => (
                <tr key={s.id}>
                  <td>{new Date(s.created_at).toLocaleString()}</td>
                  <td>
                    <StatusBadge status={s.status} />
                  </td>
                  <td>{s.finished_at ? new Date(s.finished_at).toLocaleString() : "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <Link className="btn secondary" href={`/reports/${s.id}`} style={{ marginRight: 6 }}>
                      Report
                    </Link>
                    <button className="btn secondary" onClick={() => openScan(s.id)}>
                      Findings
                    </button>
                  </td>
                </tr>
              ))}
              {scans.length === 0 && (
                <tr>
                  <td colSpan={4} className="muted">
                    No scans yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {selectedScan && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Findings</h3>
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Urgency</th>
                <th>Title</th>
                <th>Where</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id}>
                  <td>
                    <CategoryBadge category={f.category} />
                  </td>
                  <td>
                    <SeverityBadge severity={f.severity} />
                  </td>
                  <td>{f.title}</td>
                  <td className="muted" style={{ wordBreak: "break-all" }}>
                    {f.location || f.host || "—"}
                  </td>
                  <td className="muted">{f.source}</td>
                </tr>
              ))}
              {findings.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    No findings for this scan.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Shell>
  );
}
