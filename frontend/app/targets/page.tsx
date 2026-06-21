"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { StatusBadge } from "@/components/Shell";
import { api, ApiError, Target } from "@/lib/api";

export default function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [address, setAddress] = useState("");
  const [label, setLabel] = useState("");
  const [method, setMethod] = useState("dns_txt");
  const [schedule, setSchedule] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api.listTargets().then(setTargets).catch(() => undefined);
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
        schedule: schedule || null,
      });
      setAddress("");
      setLabel("");
      setSchedule("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add target");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this target and all its scans?")) return;
    await api.deleteTarget(id);
    load();
  }

  return (
    <Shell>
      <h1 className="page-title">Targets</h1>
      <p className="page-sub">Add the internet-facing assets you own. Verify ownership before scanning.</p>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Add target</h3>
        <form onSubmit={onCreate}>
          <div className="row" style={{ alignItems: "flex-end" }}>
            <div className="field" style={{ flex: 2 }}>
              <label>Hostname / IP / CIDR</label>
              <input
                placeholder="example.com or 203.0.113.10"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Label (optional)</label>
              <input value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Verification</label>
              <select value={method} onChange={(e) => setMethod(e.target.value)}>
                <option value="dns_txt">DNS TXT</option>
                <option value="http_file">HTTP file</option>
              </select>
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Schedule</label>
              <select value={schedule} onChange={(e) => setSchedule(e.target.value)}>
                <option value="">Manual</option>
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div className="field">
              <button className="btn" disabled={busy}>
                {busy ? "…" : "Add"}
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
              <th>Address</th>
              <th>Label</th>
              <th>Status</th>
              <th>Schedule</th>
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
                <td>{t.schedule || <span className="muted">manual</span>}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn danger" onClick={() => onDelete(t.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {targets.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No targets yet. Add one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
