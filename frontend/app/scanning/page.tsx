"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api, getToken } from "@/lib/api";

const STEPS = [
  "Mapping subdomains from public sources",
  "Probing which hosts are live",
  "Checking for exposed files & misconfigurations",
  "Harvesting leaked emails & secrets",
  "Verifying the organisation with Cala AI",
  "Scoring your external posture A–F",
];

export default function ScanningPage() {
  const router = useRouter();
  const [domain, setDomain] = useState("");
  const [stepIdx, setStepIdx] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    if (!getToken()) {
      router.replace("/login");
      return;
    }
    const pending =
      typeof window !== "undefined"
        ? localStorage.getItem("guarda_pending_domain")
        : null;
    if (!pending) {
      router.replace("/dashboard");
      return;
    }
    setDomain(pending);

    let polling: ReturnType<typeof setInterval> | undefined;
    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];

    function pushLog(line: string) {
      setLogs((l) => [...l.slice(-7), line]);
    }

    async function go() {
      try {
        pushLog(`$ guarda scan ${pending}`);
        const { scan_id } = await api.onboardingScan(pending as string);
        localStorage.removeItem("guarda_pending_domain");
        pushLog(`scan queued · id ${scan_id.slice(0, 8)}`);

        // Safety net: always land on the report even if the free backend is
        // slow to finish — the report renders whatever has been found so far.
        const maxWait = setTimeout(() => {
          if (!cancelled) {
            if (polling) clearInterval(polling);
            router.replace(`/reports/${scan_id}`);
          }
        }, 95_000);
        timers.push(maxWait);

        polling = setInterval(async () => {
          if (cancelled) return;
          try {
            const scan = await api.getScan(scan_id);
            if (scan.status === "running") pushLog("recon in progress…");
            if (scan.status === "completed" || scan.status === "failed") {
              if (polling) clearInterval(polling);
              pushLog("report ready ✓");
              setStepIdx(STEPS.length - 1);
              setTimeout(() => router.replace(`/reports/${scan_id}`), 900);
            }
          } catch {
            /* transient errors while the free backend warms up — keep polling */
          }
        }, 2500);
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : "Could not start the scan.",
        );
      }
    }

    go();
    const stepTimer = setInterval(
      () => setStepIdx((i) => (i < STEPS.length - 2 ? i + 1 : i)),
      2600,
    );

    return () => {
      cancelled = true;
      if (polling) clearInterval(polling);
      clearInterval(stepTimer);
      timers.forEach(clearTimeout);
    };
  }, [router]);

  if (error) {
    return (
      <div className="auth-wrap">
        <div className="auth-card" style={{ textAlign: "center" }}>
          <div className="brand" style={{ justifyContent: "center" }}>
            <span className="dot" /> Guarda
          </div>
          <p className="error">{error}</p>
          <button className="btn" onClick={() => router.replace("/dashboard")}>
            Go to dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="scan-wrap">
      <div className="scan-card">
        <div className="brand" style={{ justifyContent: "center", marginBottom: 6 }}>
          <span className="dot" /> Guarda
        </div>
        <h1 className="scan-title">
          Scanning <span className="lp-grad">{domain || "your domain"}</span>
        </h1>
        <p className="scan-sub">
          Running the same reconnaissance an attacker runs — across public
          sources. This usually takes under a minute.
        </p>

        <div className="scan-radar">
          <div className="scan-radar-sweep" />
          <div className="scan-radar-ring" />
          <div className="scan-radar-ring r2" />
          <div className="scan-radar-core" />
        </div>

        <ul className="scan-steps">
          {STEPS.map((s, i) => (
            <li
              key={s}
              className={
                i < stepIdx ? "done" : i === stepIdx ? "active" : "pending"
              }
            >
              <span className="scan-step-icon">
                {i < stepIdx ? "✓" : i === stepIdx ? "" : ""}
              </span>
              {s}
            </li>
          ))}
        </ul>

        <div className="scan-console">
          {logs.map((l, i) => (
            <div key={i}>{l}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
