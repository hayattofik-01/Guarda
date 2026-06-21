"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, IntegrationStatus } from "@/lib/api";

const ROWS: { key: keyof IntegrationStatus; name: string; purpose: string; env: string }[] = [
  { key: "supabase", name: "Supabase", purpose: "Database (Postgres)", env: "SUPABASE_DB_URL" },
  { key: "resend", name: "Resend", purpose: "Sensitive-finding email alerts", env: "RESEND_API_KEY" },
  { key: "slack", name: "Slack", purpose: "Chat alerts (optional)", env: "SLACK_WEBHOOK_URL" },
  { key: "cala", name: "Cala.ai", purpose: "Structured data / intel layer", env: "CALA_API_KEY" },
  { key: "shodan", name: "Shodan", purpose: "Exposed host/service discovery", env: "SHODAN_API_KEY" },
  { key: "censys", name: "Censys", purpose: "Host & certificate search", env: "CENSYS_API_ID/SECRET" },
  { key: "securitytrails", name: "SecurityTrails", purpose: "Subdomain & DNS data", env: "SECURITYTRAILS_API_KEY" },
  { key: "virustotal", name: "VirusTotal", purpose: "Passive DNS / subdomains", env: "VIRUSTOTAL_API_KEY" },
  { key: "nvd", name: "NVD (NIST)", purpose: "CVE intelligence", env: "NVD_API_KEY" },
];

export default function IntegrationsPage() {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [cala, setCala] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.integrations().then(setStatus).catch(() => undefined);
  }, []);

  function checkCala() {
    setCala({ loading: true });
    api.calaHealth().then(setCala).catch(() => setCala({ error: "request failed" }));
  }

  return (
    <Shell>
      <h1 className="page-title">Integrations</h1>
      <p className="page-sub">
        Guarda scans with free OSINT tools (subfinder, httpx, nuclei, gitleaks, theHarvester).
        Supabase and Resend power storage and alerts; the rest are optional enrichments.
      </p>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Service</th>
              <th>Purpose</th>
              <th>Env var</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.key}>
                <td>{r.name}</td>
                <td className="muted">{r.purpose}</td>
                <td className="mono" style={{ display: "inline-block", padding: "2px 8px" }}>
                  {r.env}
                </td>
                <td>
                  {status?.[r.key] ? (
                    <span className="tag-on">● connected</span>
                  ) : (
                    <span className="tag-off">○ not set</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <div className="flex-between">
          <div>
            <h3 style={{ margin: 0 }}>Cala.ai connectivity</h3>
            <span className="muted">Initialize the MCP session and list available tools.</span>
          </div>
          <button className="btn" onClick={checkCala}>
            Test connection
          </button>
        </div>
        {cala && <div className="mono" style={{ marginTop: 14 }}>{JSON.stringify(cala, null, 2)}</div>}
      </div>
    </Shell>
  );
}
