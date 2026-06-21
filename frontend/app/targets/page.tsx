"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { StatusBadge } from "@/components/Shell";
import { api, ApiError, Frequency, Target } from "@/lib/api";

export default function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [address, setAddress] = useState("");
  const [label, setLabel] = useState("");
  const [method, setMethod] = useState("dns_txt");
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [alertEmail, setAlertEmail] = useState("");
  const [githubTarget, setGithubTarget] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api
      .listTargets()
      .then(setTargets)
      .catch(() => undefined);
  }
  useEffect(load, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.createTarget({
        address,
        label: label || undefined,
        verification_method: method,
        frequency,
        alert_email: alertEmail || null,
        github_target: githubTarget || null,
      });
      setAddress("");
      setLabel("");
      setAlertEmail("");
      setGithubTarget("");
      setFrequency("weekly");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add asset");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Stop monitoring this asset and delete all its scans?")) return;
    await api.deleteTarget(id);
    load();
  }

  return (
    <Shell>
      <h1 className="page-title">Monitored Assets</h1>
      <p className="page-sub">
        Add the domains you own. We verify ownership, then watch them on your schedule and
        email you when something sensitive shows up.
      </p>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Add asset to monitor</h3>
        <form onSubmit={onCreate}>
          <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
            <div className="field" style={{ flex: 2, minWidth: 200 }}>
              <label>Domain / Hostname</label>
              <input
                placeholder="example.com"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 130 }}>
              <label>Label (optional)</label>
              <input value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 130 }}>
              <label>Verification</label>
              <select value={method} onChange={(e) => setMethod(e.target.value)}>
                <option value="dns_txt">DNS TXT</option>
                <option value="http_file">HTTP file</option>
              </select>
            </div>
            <div className="field" style={{ flex: 1, minWidth: 130 }}>
              <label>Scan frequency</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as Frequency)}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
          </div>
          <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
            <div className="field" style={{ flex: 2, minWidth: 200 }}>
              <label>Alert email (where we send sensitive findings)</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={alertEmail}
                onChange={(e) => setAlertEmail(e.target.value)}
              />
            </div>
            <div className="field" style={{ flex: 2, minWidth: 200 }}>
              <label>Public GitHub repo to scan for leaks (optional)</label>
              <input
                placeholder="owner/repo"
                value={githubTarget}
                onChange={(e) => setGithubTarget(e.target.value)}
              />
            </div>
            <div className="field">
              <button className="btn" disabled={busy}>
                {busy ? "…" : "Add asset"}
              </button>
            </div>
          </div>
          {error && <div className="error">{error}</div>}
        </form>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Asset</th>
              <th>Label</th>
              <th>Status</th>
              <th>Frequency</th>
              <th>Alert email</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {targets.map((t) => (
              <tr key={t.id}>
                <td>
                  <Link href={`/targets/${t.id}`} style={{ color: "var(--accent-2)" }}>
                    {t.address}
                  </Link>
                </td>
                <td>{t.label || <span className="muted">—</span>}</td>
                <td>
                  <StatusBadge status={t.status} />
                </td>
                <td style={{ textTransform: "capitalize" }}>{t.frequency}</td>
                <td>{t.alert_email || <span className="muted">—</span>}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn danger" onClick={() => onDelete(t.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {targets.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No assets yet. Add one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
