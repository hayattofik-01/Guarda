const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "guarda_token";

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
  if (
    !headers.has("Content-Type") &&
    options.body &&
    !(options.body instanceof URLSearchParams) &&
    !(options.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/admin/login")) {
      window.location.href = "/admin/login";
    }
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      const d = body.detail;
      if (typeof d === "string") {
        detail = d;
      } else if (Array.isArray(d)) {
        detail = d.map((e) => e?.msg || JSON.stringify(e)).join("; ");
      } else if (d) {
        detail = typeof d === "object" ? JSON.stringify(d) : String(d);
      }
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

// ---- Types ----
export type TargetStatus = "pending" | "verified" | "failed";
export type Severity = "info" | "low" | "medium" | "high" | "critical";
export type Frequency = "hourly" | "daily" | "weekly" | "monthly";
export type FindingCategory =
  | "sensitive_info"
  | "exposed_data"
  | "reputation_risk"
  | "footprint";

export interface Target {
  id: string;
  address: string;
  label: string | null;
  status: TargetStatus;
  verification_method: "dns_txt" | "http_file";
  verification_token: string;
  verified_at: string | null;
  frequency: Frequency;
  next_scan_at: string | null;
  last_scan_at: string | null;
  alert_email: string | null;
  alert_whatsapp: string | null;
  github_target: string | null;
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
  category: FindingCategory;
  status: "open" | "fixed" | "accepted";
  host: string | null;
  port: number | null;
  service: string | null;
  source: string;
  location: string | null;
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
  score: number;
  grade: string;
  score_summary: string;
  findings_by_severity: Record<string, number>;
  findings_by_category: Record<string, number>;
}

export interface ComplianceCheck {
  question: string;
  passed: boolean;
  detail: string;
}

export interface GdprCheck {
  article: string;
  requirement: string;
  passed: boolean;
  detail: string;
}

export interface GdprLeader {
  name: string;
  role: string;
}

export interface GdprOrganisation {
  entity_id: string;
  name: string;
  legal_name: string | null;
  industry: string | null;
  employees: string | null;
  headquarters: string | null;
  leadership: GdprLeader[];
  ultimate_parent: string | null;
}

export interface GdprIncident {
  summary: string;
  sources: string[];
}

export interface GdprAssessment {
  source: "cala" | "heuristic";
  summary: string;
  checks: GdprCheck[];
  organisation: GdprOrganisation | null;
  incidents: GdprIncident[];
}

export interface ReportItem {
  title: string;
  severity: Severity;
  severity_label: string;
  where: string;
  what_happened: string;
  what_to_do: string;
}

export interface ReportSection {
  category: FindingCategory;
  title: string;
  what_it_means: string;
  count: number;
  items: ReportItem[];
}

export interface Report {
  asset: string;
  label: string | null;
  generated_at: string;
  scan_id: string;
  overall_risk: string;
  score: number;
  grade: string;
  score_summary: string;
  compliance: ComplianceCheck[];
  gdpr: GdprAssessment;
  advice: string | null;
  advice_source: string | null;
  advice_status: string | null;
  headline: string;
  totals: Record<string, number | Record<string, number>>;
  next_steps: string[];
  sections: ReportSection[];
}

export interface DocumentCheck {
  article: string;
  requirement: string;
  passed: boolean;
  detail: string;
}

export interface GuardaDocument {
  id: string;
  filename: string;
  doc_type: string;
  status: "queued" | "running" | "completed" | "failed";
  compliance_status: "compliant" | "gaps" | "non_compliant" | null;
  compliance_score: number | null;
  summary: string | null;
  advice: string | null;
  error: string | null;
  frequency: Frequency;
  next_check_at: string | null;
  last_checked_at: string | null;
  created_at: string;
}

export interface GuardaDocumentDetail extends GuardaDocument {
  checks: DocumentCheck[];
}

export interface VerificationInstructions {
  method: "dns_txt" | "http_file";
  token: string;
  instructions: string;
}

export interface IntegrationStatus {
  supabase: boolean;
  resend: boolean;
  whatsapp: boolean;
  cala: boolean;
  shodan: boolean;
  censys: boolean;
  securitytrails: boolean;
  virustotal: boolean;
  nvd: boolean;
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
    frequency?: Frequency;
    alert_email?: string | null;
    alert_whatsapp?: string | null;
    github_target?: string | null;
  }) => request<Target>("/api/targets", { method: "POST", body: JSON.stringify(payload) }),
  updateTarget: (
    id: string,
    payload: {
      frequency?: Frequency;
      alert_email?: string | null;
      alert_whatsapp?: string | null;
      github_target?: string | null;
    },
  ) => request<Target>(`/api/targets/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteTarget: (id: string) => request<void>(`/api/targets/${id}`, { method: "DELETE" }),
  verification: (id: string) =>
    request<VerificationInstructions>(`/api/targets/${id}/verification`),
  verifyTarget: (id: string) =>
    request<Target>(`/api/targets/${id}/verify`, { method: "POST" }),

  startScan: (targetId: string) =>
    request<Scan>(`/api/scans/targets/${targetId}`, { method: "POST" }),
  listScans: (targetId: string) => request<Scan[]>(`/api/scans/targets/${targetId}`),
  getScan: (id: string) => request<ScanDetail>(`/api/scans/${id}`),
  getReport: (id: string) => request<Report>(`/api/scans/${id}/report`),

  listFindings: (severity?: Severity) =>
    request<Finding[]>(`/api/findings${severity ? `?severity=${severity}` : ""}`),
  updateFinding: (id: string, status: string) =>
    request<Finding>(`/api/findings/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  onboardingScan: (domain: string) =>
    request<{ scan_id: string; target_id: string }>("/api/onboarding/scan", {
      method: "POST",
      body: JSON.stringify({ domain }),
    }),

  listDocuments: () => request<GuardaDocument[]>("/api/documents"),
  getDocument: (id: string) => request<GuardaDocumentDetail>(`/api/documents/${id}`),
  uploadDocument: (file: File, docType = "document") => {
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    return request<GuardaDocument>("/api/documents", { method: "POST", body: form });
  },
  recheckDocument: (id: string) =>
    request<GuardaDocument>(`/api/documents/${id}/recheck`, { method: "POST" }),
  deleteDocument: (id: string) =>
    request<void>(`/api/documents/${id}`, { method: "DELETE" }),
};
