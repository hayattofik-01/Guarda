const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "perimeter_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---- Auth ----
export async function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password });
  const data = await request<{ access_token: string }>("/api/auth/login", {
    method: "POST",
    body,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  setToken(data.access_token);
}

export async function register(email: string, password: string) {
  const data = await request<{ access_token: string }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
}

// ---- Types ----
export type TargetStatus = "pending" | "verified" | "failed";
export type Severity = "info" | "low" | "medium" | "high" | "critical";

export interface Target {
  id: string;
  address: string;
  label: string | null;
  status: TargetStatus;
  verification_method: "dns_txt" | "http_file";
  verification_token: string;
  verified_at: string | null;
  schedule: string | null;
  created_at: string;
}

export interface Scan {
  id: string;
  target_id: string;
  status: "queued" | "running" | "completed" | "failed";
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  created_at: string;
}

export interface Finding {
  id: string;
  scan_id: string;
  title: string;
  description: string | null;
  severity: Severity;
  status: "open" | "fixed" | "accepted";
  host: string | null;
  port: number | null;
  service: string | null;
  source: string;
  cve_id: string | null;
  cvss_score: number | null;
  priority_score: number | null;
  remediation: string | null;
  reference: string | null;
  created_at: string;
}

export interface ScanDetail extends Scan {
  findings: Finding[];
}

export interface DashboardStats {
  targets: number;
  verified_targets: number;
  total_scans: number;
  open_findings: number;
  findings_by_severity: Record<string, number>;
}

export interface VerificationInstructions {
  method: "dns_txt" | "http_file";
  token: string;
  instructions: string;
}

export interface IntegrationStatus {
  cala: boolean;
  shodan: boolean;
  censys: boolean;
  securitytrails: boolean;
  virustotal: boolean;
  nvd: boolean;
  sendgrid: boolean;
  slack: boolean;
}

// ---- Endpoints ----
export const api = {
  me: () => request<{ id: string; email: string }>("/api/auth/me"),
  stats: () => request<DashboardStats>("/api/dashboard/stats"),

  listTargets: () => request<Target[]>("/api/targets"),
  getTarget: (id: string) => request<Target>(`/api/targets/${id}`),
  createTarget: (payload: {
    address: string;
    label?: string;
    verification_method?: string;
    schedule?: string | null;
  }) => request<Target>("/api/targets", { method: "POST", body: JSON.stringify(payload) }),
  deleteTarget: (id: string) => request<void>(`/api/targets/${id}`, { method: "DELETE" }),
  verification: (id: string) =>
    request<VerificationInstructions>(`/api/targets/${id}/verification`),
  verifyTarget: (id: string) =>
    request<Target>(`/api/targets/${id}/verify`, { method: "POST" }),

  startScan: (targetId: string) =>
    request<Scan>(`/api/scans/targets/${targetId}`, { method: "POST" }),
  listScans: (targetId: string) => request<Scan[]>(`/api/scans/targets/${targetId}`),
  getScan: (id: string) => request<ScanDetail>(`/api/scans/${id}`),

  listFindings: (severity?: Severity) =>
    request<Finding[]>(`/api/findings${severity ? `?severity=${severity}` : ""}`),
  updateFinding: (id: string, status: string) =>
    request<Finding>(`/api/findings/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  integrations: () => request<IntegrationStatus>("/api/integrations/status"),
  calaHealth: () => request<Record<string, unknown>>("/api/integrations/cala/health"),
};
