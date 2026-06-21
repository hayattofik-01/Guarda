"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, DashboardStats } from "@/lib/api";

const SEVERITIES = ["critical", "high", "medium", "low", "info"];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    api.stats().then(setStats).catch(() => undefined);
  }, []);

  return (
    <Shell>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">Your external attack surface at a glance.</p>

      <div className="cards">
        <div className="card">
          <div className="label">Targets</div>
          <div className="stat">{stats?.targets ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Verified</div>
          <div className="stat">{stats?.verified_targets ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Scans run</div>
          <div className="stat">{stats?.total_scans ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Open findings</div>
          <div className="stat">{stats?.open_findings ?? "—"}</div>
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Open findings by severity</h3>
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {SEVERITIES.map((sev) => (
              <tr key={sev}>
                <td>
                  <span className={`badge sev-${sev}`}>{sev}</span>
                </td>
                <td>{stats?.findings_by_severity?.[sev] ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
