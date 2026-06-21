"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/api";

const NIGHTMARES = [
  {
    title: "A customer reports a breach",
    body: "Their data was exposed — and the first you hear of it is the email asking why.",
  },
  {
    title: "An enterprise deal dies",
    body: "Your prospect sends a security questionnaire. You fail it, and the deal goes quiet.",
  },
  {
    title: "A GDPR notice lands",
    body: "A regulator found something public about your company before you did.",
  },
];

const LEAKS = [
  "A job post naming the exact database software you run.",
  "A PDF with an internal server path buried in its metadata.",
  "A forgotten staging server still live on a subdomain.",
  "A DNS record that tells attackers which email-security vendor you use.",
];

const STEPS = [
  {
    n: "1",
    title: "We run the recon an attacker runs",
    body: "Guarda queries public sources — subdomains, live hosts, exposures, leaked secrets, harvested emails, DNS and certificate records — the same footprint a hacker maps before they strike.",
  },
  {
    n: "2",
    title: "We score it A to F",
    body: "Every finding rolls up into one grade you can read in a glance. No CVSS math, no dashboards to learn.",
  },
  {
    n: "3",
    title: "Plain English, one action each",
    body: "Each finding is explained in business language with exactly one thing to do about it. Found in ~40 seconds.",
  },
];

export default function Landing() {
  const router = useRouter();
  const [domain, setDomain] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(!!getToken());
  }, []);

  function goCheck(e?: FormEvent) {
    e?.preventDefault();
    const d = domain.trim();
    if (d && typeof window !== "undefined") {
      localStorage.setItem("guarda_pending_domain", d);
    }
    router.push("/login");
  }

  return (
    <div className="landing">
      <header className="lp-nav">
        <div className="brand">
          <span className="dot" />
          <span>Guarda</span>
        </div>
        <div className="lp-nav-actions">
          {loggedIn ? (
            <Link className="btn" href="/dashboard">
              Open dashboard
            </Link>
          ) : (
            <>
              <Link className="lp-link" href="/login">
                Sign in
              </Link>
              <button className="btn" onClick={() => goCheck()}>
                Check my score
              </button>
            </>
          )}
        </div>
      </header>

      <section className="lp-hero">
        <div className="lp-eyebrow">External security monitoring for SaaS founders</div>
        <h1>
          Know your external security score.
          <br />
          <span className="lp-grad">Close the enterprise deal.</span>
        </h1>
        <p className="lp-lede">
          You shipped the product. You&apos;re selling. Then someone looks at your domain from the
          outside and finds something you didn&apos;t know was there. Guarda finds it first — and
          tells you what to do in plain English.
        </p>
        <form className="lp-domain" onSubmit={goCheck}>
          <input
            placeholder="yourcompany.com"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            aria-label="Your domain"
          />
          <button className="btn" type="submit">
            Check my score →
          </button>
        </form>
        <div className="lp-trust">Enter your domain · Know your score · No security engineer required</div>
      </section>

      <section className="lp-section">
        <h2 className="lp-h2">It always starts the same way</h2>
        <p className="lp-sub">
          Every nightmare below begins with someone looking at your company from the outside — and
          finding something you put there without knowing it.
        </p>
        <div className="lp-grid">
          {NIGHTMARES.map((c) => (
            <div className="lp-card" key={c.title}>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-section lp-band">
        <h2 className="lp-h2">You put it all there. You just don&apos;t know it.</h2>
        <ul className="lp-leaks">
          {LEAKS.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>

      <section className="lp-section">
        <h2 className="lp-h2">How Guarda works</h2>
        <div className="lp-grid">
          {STEPS.map((s) => (
            <div className="lp-step" key={s.n}>
              <span className="lp-step-n">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
          ))}
        </div>
        <div className="lp-score-demo">
          <div className="grade-badge grade-F">F</div>
          <div>
            <div className="lp-score-title">Your external security score</div>
            <p className="lp-score-body">
              One letter, updated on every scan. This finding — a leaked AWS key in a public job
              post — has been visible for three months. Guarda found it in 40 seconds.
            </p>
          </div>
        </div>
      </section>

      <section className="lp-section lp-band">
        <div className="lp-two">
          <div>
            <h2 className="lp-h2 lp-left">Alerts on WhatsApp, before your first coffee</h2>
            <p className="lp-sub lp-left">
              Run a scan every hour overnight. When something new appears, you get a WhatsApp message
              with the one thing you need to know and what to do about it. No dashboard. No login.
            </p>
          </div>
          <div className="lp-chat">
            <div className="lp-bubble">
              <strong>Guarda alert — yourcompany.com</strong>
              <br />
              Security score dropped to D.
              <br />
              New: exposed .env file on staging.
              <br />
              Fix: block public access to /.env.
            </div>
          </div>
        </div>
      </section>

      <section className="lp-section">
        <h2 className="lp-h2">Pass the security questionnaire. Win the deal.</h2>
        <p className="lp-sub">
          Your first enterprise customer sends a 40-question security review. Most early founders
          fail it — not because the product is insecure, but because nobody ever looked at their
          external posture. Guarda gives you that view and a professional report you hand straight to
          the prospect.
        </p>
        <p className="lp-sub">
          One enterprise deal you close because of that report is worth more than years of
          subscription.
        </p>
      </section>

      <section className="lp-section lp-band">
        <h2 className="lp-h2">Built for the founder, not the auditor</h2>
        <div className="lp-pricing">
          <div className="lp-price-card lp-them">
            <div className="lp-price-name">Intruder · Detectify · Tenable</div>
            <div className="lp-price-amt">€100+/mo</div>
            <ul>
              <li>Need a security engineer to operate</li>
              <li>Built for audits, not founders</li>
              <li>Technical output to decode</li>
            </ul>
          </div>
          <div className="lp-price-card lp-us">
            <div className="lp-price-name">Guarda</div>
            <div className="lp-price-amt">
              €99<span>/mo</span>
            </div>
            <ul>
              <li>Self-serve — live in minutes</li>
              <li>Plain English, A–F score</li>
              <li>Hourly scans + WhatsApp alerts</li>
              <li>Enterprise-ready shareable report</li>
            </ul>
            <button className="btn" onClick={() => goCheck()}>
              Check my score
            </button>
          </div>
        </div>
      </section>

      <section className="lp-final">
        <h2>Enter your domain. Know your score. Close the deal.</h2>
        <form className="lp-domain" onSubmit={goCheck}>
          <input
            placeholder="yourcompany.com"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            aria-label="Your domain"
          />
          <button className="btn" type="submit">
            Check my score →
          </button>
        </form>
      </section>

      <footer className="lp-footer">
        <span>Guarda — We watch. We detect. We guide.</span>
        <span className="muted">Only scan assets you own or are authorized to test.</span>
      </footer>
    </div>
  );
}
