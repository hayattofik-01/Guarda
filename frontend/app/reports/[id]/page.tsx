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
      <div className="flex-between report-actions" style={{ marginBottom: 16 }}>
        <h1 className="page-title" style={{ margin: 0 }}>
          Report — {report.asset}
        </h1>
        <div className="row">
          <button className="btn secondary" onClick={() => window.print()}>
            Share / Print
          </button>
          <button className="btn secondary" onClick={() => router.back()}>
            ← Back
          </button>
        </div>
      </div>

      <div className="report-hero">
        <div className="row" style={{ gap: 18, alignItems: "center", marginBottom: 14 }}>
          <div className={`grade-badge grade-${report.grade}`}>{report.grade}</div>
          <div>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>
              External security score · {report.score}/100
            </div>
            <div style={{ fontSize: 15 }}>{report.score_summary}</div>
          </div>
        </div>
        <h1>{report.headline}</h1>
        <span className={`risk-pill ${RISK_CLASS[report.overall_risk] || "risk-some"}`}>
          {report.overall_risk}
        </span>
        <p className="muted" style={{ marginBottom: 0, marginTop: 14 }}>
          Generated {new Date(report.generated_at).toLocaleString()} ·{" "}
          {String(report.totals.findings)} finding(s)
        </p>
      </div>

      {report.compliance.length > 0 && (
        <div className="panel compliance">
          <h3 style={{ marginTop: 0 }}>Security questionnaire readiness</h3>
          <p className="muted" style={{ marginTop: 0 }}>
            How your external posture answers the questions an enterprise prospect will ask.
          </p>
          <ul>
            {report.compliance.map((c, i) => (
              <li key={i}>
                <span className={`check-mark ${c.passed ? "check-pass" : "check-fail"}`}>
                  {c.passed ? "\u2713" : "\u2717"}
                </span>
                <div>
                  <div>{c.question}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{c.detail}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.gdpr && report.gdpr.checks.length > 0 && (
        <div className="panel compliance">
          <div className="flex-between" style={{ alignItems: "flex-start" }}>
            <h3 style={{ marginTop: 0 }}>GDPR compliance</h3>
            <span className={`gdpr-source ${report.gdpr.source}`}>
              {report.gdpr.source === "cala"
                ? "Assessed by Cala AI"
                : "Automated assessment"}
            </span>
          </div>
          <p className="muted" style={{ marginTop: 0 }}>
            {report.gdpr.summary}
          </p>
          <ul>
            {report.gdpr.checks.map((c, i) => (
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

          {report.gdpr.organisation && (
            <div className="cala-org">
              <div className="cala-org-head">
                Organisation verified by Cala
              </div>
              <dl className="cala-facts">
                {report.gdpr.organisation.legal_name && (
                  <div><dt>Legal name</dt><dd>{report.gdpr.organisation.legal_name}</dd></div>
                )}
                {report.gdpr.organisation.industry && (
                  <div><dt>Industry</dt><dd>{report.gdpr.organisation.industry}</dd></div>
                )}
                {report.gdpr.organisation.employees && (
                  <div><dt>Employees</dt><dd>{report.gdpr.organisation.employees}</dd></div>
                )}
                {report.gdpr.organisation.headquarters && (
                  <div><dt>Headquarters</dt><dd>{report.gdpr.organisation.headquarters}</dd></div>
                )}
                {report.gdpr.organisation.ultimate_parent && (
                  <div><dt>Ultimate parent</dt><dd>{report.gdpr.organisation.ultimate_parent}</dd></div>
                )}
                {report.gdpr.organisation.leadership.length > 0 && (
                  <div>
                    <dt>Leadership</dt>
                    <dd>
                      {report.gdpr.organisation.leadership
                        .map((l) => `${l.name} (${l.role})`)
                        .join(", ")}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {report.gdpr.incidents.length > 0 && (
            <div className="cala-incidents">
              <div className="cala-org-head">Publicly reported incidents (via Cala)</div>
              {report.gdpr.incidents.map((inc, i) => (
                <div key={i} className="cala-incident">
                  <p style={{ margin: "4px 0" }}>{inc.summary}</p>
                  {inc.sources.length > 0 && (
                    <div className="cala-sources">
                      {inc.sources.map((s, j) => (
                        <a key={j} href={s} target="_blank" rel="noopener noreferrer">
                          Source {j + 1}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
