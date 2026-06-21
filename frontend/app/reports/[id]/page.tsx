"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Shell, { SeverityBadge } from "@/components/Shell";
import { api, Report } from "@/lib/api";

const RISK_CLASS: Record<string, string> = {
  "Action needed": "risk-action",
  "Some attention needed": "risk-some",
  "Looking good": "risk-clear",
  "All clear": "risk-clear",
};

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getReport(id)
      .then(setReport)
      .catch(() => setError("Could not load this report."));
  }, [id]);

  if (error) {
    return (
      <Shell>
        <p className="error">{error}</p>
      </Shell>
    );
  }
  if (!report) {
    return (
      <Shell>
        <p className="muted">Generating your report…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="flex-between" style={{ marginBottom: 16 }}>
        <h1 className="page-title" style={{ margin: 0 }}>
          Report — {report.asset}
        </h1>
        <button className="btn secondary" onClick={() => router.back()}>
          ← Back
        </button>
      </div>

      <div className="report-hero">
        <h1>{report.headline}</h1>
        <span className={`risk-pill ${RISK_CLASS[report.overall_risk] || "risk-some"}`}>
          {report.overall_risk}
        </span>
        <p className="muted" style={{ marginBottom: 0, marginTop: 14 }}>
          Generated {new Date(report.generated_at).toLocaleString()} ·{" "}
          {String(report.totals.findings)} finding(s)
        </p>
      </div>

      {report.next_steps.length > 0 && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>What to do next</h3>
          <ul className="next-steps">
            {report.next_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ul>
        </div>
      )}

      {report.sections.map((section) => (
        <div key={section.category} className="panel">
          <h3 style={{ marginTop: 0 }}>
            {section.title} <span className="muted">({section.count})</span>
          </h3>
          <p className="muted" style={{ marginTop: 0 }}>
            {section.what_it_means}
          </p>
          {section.items.map((item, i) => (
            <div key={i} className="report-item">
              <div className="flex-between">
                <strong>{item.title}</strong>
                <SeverityBadge severity={item.severity} />
              </div>
              {item.where && <div className="where">{item.where}</div>}
              {item.what_happened && (
                <div style={{ marginTop: 6 }}>{item.what_happened}</div>
              )}
              <div className="todo">
                <strong>What to do:</strong> {item.what_to_do}
              </div>
            </div>
          ))}
        </div>
      ))}

      {report.sections.length === 0 && (
        <div className="panel muted">
          Nothing notable found in this scan. We&apos;ll keep watching.
        </div>
      )}
    </Shell>
  );
}
