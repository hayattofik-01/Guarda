"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, login, register } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      const pending =
        typeof window !== "undefined"
          ? localStorage.getItem("guarda_pending_domain")
          : null;
      if (pending) {
        router.replace("/scanning");
      } else {
        router.replace("/dashboard");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="brand" style={{ marginBottom: 12 }}>
          <span className="dot" /> Guarda
        </div>
        <p className="muted" style={{ marginTop: 0 }}>
          Know your external security score. Sign in to check your domain, fix
          exposures in plain English, and pass enterprise security questionnaires.
        </p>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>
          {error && <div className="error">{error}</div>}
          <button className="btn" type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <p className="muted" style={{ marginBottom: 0, marginTop: 16, textAlign: "center" }}>
          {mode === "login" ? "No account?" : "Have an account?"}{" "}
          <a
            style={{ color: "var(--accent-2)", cursor: "pointer" }}
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Register" : "Sign in"}
          </a>
        </p>
      </div>
    </div>
  );
}
