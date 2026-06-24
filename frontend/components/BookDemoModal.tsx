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
        <button className="modal-close" onClick={onClose}>
          &times;
        </button>

        {status === "sent" ? (
          <div className="modal-success">
            <div className="modal-success-icon">&#10003;</div>
            <h3>Demo booked!</h3>
            <p>We&apos;ll reach out within 24 hours to schedule your live scan.</p>
            <button className="lp-cta" onClick={onClose}>
              Close
            </button>
          </div>
        ) : (
          <>
            <h3 className="modal-title">Book a live demo</h3>
            <p className="modal-sub">
              We&apos;ll scan your actual domain on the call. 20 minutes. No commitment.
            </p>
            <form onSubmit={handleSubmit} className="modal-form">
              <input
                type="text"
                placeholder="Your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="modal-input"
              />
              <input
                type="email"
                placeholder="Work email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="modal-input"
              />
              <input
                type="text"
                placeholder="Company domain (e.g. acme.com)"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="modal-input"
              />
              <button
                type="submit"
                className="lp-cta modal-submit"
                disabled={status === "sending"}
              >
                {status === "sending" ? "Sending..." : "Book my demo →"}
              </button>
              {status === "error" && (
                <p className="modal-error">Something went wrong. Please try again.</p>
              )}
            </form>
          </>
        )}
      </div>
    </div>
  );
}
