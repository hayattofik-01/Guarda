"use client";

import { useState, FormEvent } from "react";

interface BookDemoModalProps {
  open: boolean;
  onClose: () => void;
}

export default function BookDemoModal({ open, onClose }: BookDemoModalProps) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  if (!open) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("sending");
    try {
      const res = await fetch("/api/book-demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, company }),
      });
      if (res.ok) {
        setStatus("sent");
        setEmail("");
        setName("");
        setCompany("");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>

        {status === "sent" ? (
          <div className="modal-success">
            <div className="modal-success-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3>You&apos;re on the list!</h3>
            <p>We&apos;ll reach out within 24 hours to schedule your live scan.</p>
            <button className="modal-submit-btn" onClick={onClose}>
              Got it
            </button>
          </div>
        ) : (
          <>
            <div className="modal-badge">
              <span className="modal-badge-dot" />
              Spots available this week
            </div>
            <h3 className="modal-title">Book a live demo</h3>
            <p className="modal-sub">
              We&apos;ll scan your actual domain on the call &mdash; 20 min, no commitment.
            </p>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="modal-field">
                <svg className="modal-field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" />
                </svg>
                <input
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="modal-input"
                />
              </div>
              <div className="modal-field">
                <svg className="modal-field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M22 7l-10 6L2 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <input
                  type="email"
                  placeholder="Work email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="modal-input"
                />
              </div>
              <div className="modal-field">
                <svg className="modal-field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                  <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10A15.3 15.3 0 0112 2z" stroke="currentColor" strokeWidth="2" />
                </svg>
                <input
                  type="text"
                  placeholder="Company domain (e.g. acme.com)"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="modal-input"
                />
              </div>
              <button
                type="submit"
                className="modal-submit-btn"
                disabled={status === "sending"}
              >
                {status === "sending" ? "Sending..." : "Book my demo"}
              </button>
              {status === "error" && (
                <p className="modal-error">Something went wrong. Please try again.</p>
              )}
            </form>
            <div className="modal-divider">or</div>
            <div className="modal-trust">
              <span className="modal-trust-item">
                <svg className="modal-trust-icon" width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                No spam, ever
              </span>
              <span className="modal-trust-item">
                <svg className="modal-trust-icon" width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                  <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                20 min call
              </span>
              <span className="modal-trust-item">
                <svg className="modal-trust-icon" width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M22 11.08V12a10 10 0 11-5.93-9.14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M22 4L12 14.01l-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Free scan included
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
