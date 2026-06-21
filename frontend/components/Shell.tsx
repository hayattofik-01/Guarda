"use client";

import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { api, clearToken, getToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/targets", label: "Monitored Assets" },
  { href: "/findings", label: "Findings" },
  { href: "/integrations", label: "Integrations" },
];

export default function Shell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [email, setEmail] = useState<string>("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .me()
      .then((u) => {
        setEmail(u.email);
        setReady(true);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  if (!ready) {
    return (
      <div className="auth-wrap">
        <span className="muted">Loading…</span>
      </div>
    );
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="dot" />
          <span>
            Guarda
            <span className="tagline">We watch. We detect. We guide.</span>
          </span>
        </div>
        <nav className="nav">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname.startsWith(item.href) ? "active" : ""}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div style={{ position: "absolute", bottom: 20, left: 14, right: 14 }}>
          <div className="muted" style={{ fontSize: 12, marginBottom: 8, wordBreak: "break-all" }}>
            {email}
          </div>
          <button
            className="btn secondary"
            style={{ width: "100%" }}
            onClick={() => {
              clearToken();
              router.replace("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <span className={`badge sev-${severity}`}>{severity}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge status-${status}`}>{status}</span>;
}

const CATEGORY_LABELS: Record<string, string> = {
  sensitive_info: "Sensitive Info",
  exposed_data: "Exposed Data",
  reputation_risk: "Reputation Risk",
  footprint: "Footprint",
};

export function CategoryBadge({ category }: { category: string }) {
  return (
    <span className={`badge cat-${category}`}>{CATEGORY_LABELS[category] || category}</span>
  );
}
