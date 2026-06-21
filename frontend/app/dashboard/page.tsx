"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, DashboardStats } from "@/lib/api";

const SEVERITIES = ["critical", "high", "medium", "low", "info"];

const CATEGORY_TILES = [
  {
    key: "sensitive_info",
    label: "Sensitive Information Found",
    desc: "Leaked passwords, API keys, or staff emails visible to anyone.",
  },
  {
    key: "exposed_data",
    label: "Exposed Data Detected",
    desc: "Private files, folders, or admin pages reachable by the public.",
  },
  {
    key: "reputation_risk",
    label: "Reputation Risk Identified",
    desc: "Issues that could let attackers impersonate or harm your brand.",
  },
  {
    key: "footprint",
    label: "Your Digital Footprint",
    desc: "Public-facing assets that make up your online presence.",
  },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch(() => undefined);
  }, []);

  return (
    <Shell>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">Your digital footprint and exposures at a glance.</p>

      <div className="cat-tiles">
        {CATEGORY_TILES.map((tile) => (
          <div key={tile.key} className={`cat-tile ${tile.key}`}>
            <div className="stat">{stats?.findings_by_category?.[tile.key] ?? "—"}</div>
            <div className="label">{tile.label}</div>
            <div className="desc">{tile.desc}</div>
          </div>
        ))}
      </div>

      <div className="cards">
        <div className="card">
          <div className="label">Monitored assets</div>
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
        <h3 style={{ marginTop: 0 }}>Open findings by urgency</h3>
        <table>
          <thead>
            <tr>
              <th>Urgency</th>
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
