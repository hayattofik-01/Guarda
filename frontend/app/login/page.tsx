"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, login } from "@/lib/api";

const DEMO_URL =
  "mailto:founders@guarda.app?subject=Book%20a%20Guarda%20demo&body=Hi%20Guarda%20team%2C%20I%27d%20like%20to%20book%20a%20demo.%20My%20company%20domain%20is%3A";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
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
          Sign in to your Guarda dashboard.
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
            {busy ? "…" : "Sign in"}
          </button>
        </form>
        <p className="muted" style={{ marginBottom: 0, marginTop: 16, textAlign: "center" }}>
          Want to try Guarda?{" "}
          <a style={{ color: "var(--accent-2)" }} href={DEMO_URL}>
            Book a demo
          </a>
        </p>
      </div>
    </div>
  );
}
