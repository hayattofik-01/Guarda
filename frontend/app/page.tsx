"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getToken } from "@/lib/api";
import FadeInSection from "@/components/FadeInSection";
import BookDemoModal from "@/components/BookDemoModal";

const ParticleField = dynamic(() => import("@/components/ParticleField"), {
  ssr: false,
});

const NIGHTMARES = [
  {
    icon: "🔓",
    title: "A breach — and you're the last to know",
    body: "A customer's data leaks. The first you hear about it is their angry email, not your monitoring. That's a churned account and a reputation hit you can't undo.",
  },
  {
    icon: "💀",
    title: "The enterprise deal goes silent",
    body: "You're two calls from closing a six-figure contract. They send a security questionnaire. You can't answer it. They ghost. Game over.",
  },
  {
    icon: "🕵️",
    title: "Your staging server is wide open — and indexed",
    body: "A forgotten subdomain with admin access, no auth, and real user data. Google found it before you did. So did someone else.",
  },
];

const LEAKS = [
  { text: "A job post naming the exact database software you run", detail: "attackers know your stack" },
  { text: "A PDF with an internal server path in its metadata", detail: "your infrastructure leaks in documents" },
  { text: "A forgotten staging server, live on a public subdomain", detail: "an open door nobody's watching" },
  { text: "A DNS record revealing your email-security vendor", detail: "your defense is public knowledge" },
  { text: "An exposed .env file with API keys in plaintext", detail: "secrets hiding in plain sight" },
];

const STEPS = [
  {
    n: "1",
    title: "We run the same recon an attacker runs",
    body: "Subdomains, live hosts, leaked secrets, harvested emails, DNS records, certificate transparency logs — the full reconnaissance an adversary maps before they strike. Done in under 60 seconds.",
  },
  {
    n: "2",
    title: "One score: A to F",
    body: "Every finding rolls into one letter grade. No CVSS scores, no security jargon, no dashboards to learn. Your board and your prospect both understand it instantly.",
  },
  {
    n: "3",
    title: "Plain English. One action per finding.",
    body: "Each exposure comes with exactly one thing to do about it, written so any founder can execute — no security engineer required.",
  },
];

const SOCIAL_PROOF = [
  { metric: "40s", label: "average scan time" },
  { metric: "A–F", label: "one-glance score" },
  { metric: "0", label: "security engineers needed" },
  { metric: "24/7", label: "continuous monitoring" },
];

export default function Landing() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    setLoggedIn(!!getToken());
    function onScroll() {
      setScrolled(window.scrollY > 60);
    }
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="landing">
      <ParticleField />

      {/* ── Nav ── */}
      <header className={`lp-nav${scrolled ? " lp-nav-scrolled" : ""}`}>
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
              <Link className="lp-link" href="/admin/login">
                Sign in
              </Link>
              <button className="btn btn-glow" onClick={() => setDemoOpen(true)}>
                Book a demo
              </button>
            </>
          )}
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="lp-hero">
        <FadeInSection>
          <div className="lp-eyebrow">External attack surface monitoring for SaaS founders</div>
          <h1>
            Hackers already see your weak spots.
            <br />
            <span className="lp-grad">Shouldn&apos;t you?</span>
          </h1>
          <p className="lp-lede">
            Right now, someone could be mapping your company&apos;s digital footprint — exposed servers,
            leaked secrets, misconfigured DNS. <strong>Guarda finds everything an attacker finds</strong>,
            gives you a single A–F score, and tells you exactly what to fix. In plain English.
            In under 60 seconds.
          </p>
        </FadeInSection>
        <FadeInSection delay={200}>
          <div className="lp-hero-cta">
            <button className="btn btn-hero btn-glow" onClick={() => setDemoOpen(true)}>
              Book a live demo →
            </button>
            <div className="lp-trust">We&apos;ll scan your actual domain on the call. 20 minutes. No commitment.</div>
          </div>
        </FadeInSection>
        <FadeInSection delay={400}>
          <div className="lp-metrics">
            {SOCIAL_PROOF.map((m) => (
              <div className="lp-metric" key={m.label}>
                <span className="lp-metric-num">{m.metric}</span>
                <span className="lp-metric-label">{m.label}</span>
              </div>
            ))}
          </div>
        </FadeInSection>
      </section>

      {/* ── Nightmare scenarios ── */}
      <section className="lp-section">
        <FadeInSection>
          <h2 className="lp-h2">This is how founders lose deals, customers, and sleep</h2>
          <p className="lp-sub">
            Every scenario below starts the same way: someone looks at your company from the outside
            and finds something you didn&apos;t know was there.
          </p>
        </FadeInSection>
        <div className="lp-grid">
          {NIGHTMARES.map((c, i) => (
            <FadeInSection key={c.title} delay={i * 120}>
              <div className="lp-card lp-card-hover">
                <div className="lp-card-icon">{c.icon}</div>
                <h3>{c.title}</h3>
                <p>{c.body}</p>
              </div>
            </FadeInSection>
          ))}
        </div>
      </section>

      {/* ── Leaks ── */}
      <section className="lp-section lp-band">
        <FadeInSection>
          <h2 className="lp-h2">You put it all out there. You just don&apos;t know it yet.</h2>
          <p className="lp-sub">
            These are real exposures we find on SaaS companies every single day.
            Every one of them is publicly visible, right now, to anyone who looks.
          </p>
        </FadeInSection>
        <ul className="lp-leaks">
          {LEAKS.map((l, i) => (
            <FadeInSection key={l.text} delay={i * 80} direction="left">
              <li>
                <span className="lp-leak-text">{l.text}</span>
                <span className="lp-leak-detail">— {l.detail}</span>
              </li>
            </FadeInSection>
          ))}
        </ul>
      </section>

      {/* ── How it works ── */}
      <section className="lp-section">
        <FadeInSection>
          <h2 className="lp-h2">Three steps. Zero security expertise.</h2>
          <p className="lp-sub">
            Guarda does the work of a penetration tester — in 40 seconds, not 40 days.
          </p>
        </FadeInSection>
        <div className="lp-grid">
          {STEPS.map((s, i) => (
            <FadeInSection key={s.n} delay={i * 120}>
              <div className="lp-step lp-card-hover">
                <span className="lp-step-n">{s.n}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
            </FadeInSection>
          ))}
        </div>
        <FadeInSection delay={400}>
          <div className="lp-score-journey">
            <div className="lp-score-title">Watch the score transform</div>
            <p className="lp-score-sub">
              Real startup. Real results. Every fix takes minutes — not meetings.
            </p>
            <div className="lp-score-timeline">
              <div className="lp-score-step">
                <div className="grade-badge grade-F">F</div>
                <span className="lp-score-label">Day 1</span>
                <span className="lp-score-detail">3 leaked keys, open staging, no headers</span>
              </div>
              <div className="lp-score-arrow">→</div>
              <div className="lp-score-step">
                <div className="grade-badge grade-C">C</div>
                <span className="lp-score-label">Day 3</span>
                <span className="lp-score-detail">Keys rotated, staging locked down</span>
              </div>
              <div className="lp-score-arrow">→</div>
              <div className="lp-score-step">
                <div className="grade-badge grade-A">A</div>
                <span className="lp-score-label">Day 7</span>
                <span className="lp-score-detail">Enterprise-ready. Deal closed.</span>
              </div>
            </div>
          </div>
        </FadeInSection>
      </section>

      {/* ── Video demos ── */}
      <section className="lp-section">
        <FadeInSection>
          <h2 className="lp-h2">See it in action</h2>
          <p className="lp-sub">
            Real scans. Real reports. Plain-English fixes you can act on today.
          </p>
        </FadeInSection>
        <FadeInSection delay={150}>
          <div className="lp-videos">
            <div className="lp-video">
              <video controls preload="metadata" poster="/videos/scan-poster.png">
                <source src="/videos/how-it-works-scan.mp4" type="video/mp4" />
              </video>
              <div className="lp-video-cap">
                <strong>1 · Enter your domain, watch the scan</strong>
                <span>The same recon an attacker runs — live, in under a minute.</span>
              </div>
            </div>
            <div className="lp-video">
              <video controls preload="metadata" poster="/videos/report-poster.png">
                <source src="/videos/how-it-works-report.mp4" type="video/mp4" />
              </video>
              <div className="lp-video-cap">
                <strong>2 · Get your score &amp; report</strong>
                <span>An A–F grade with plain-English fixes and actionable next steps.</span>
              </div>
            </div>
          </div>
        </FadeInSection>
      </section>

      {/* ── WhatsApp alerts ── */}
      <section className="lp-section lp-band">
        <FadeInSection>
          <div className="lp-two">
            <div>
              <h2 className="lp-h2 lp-left">Wake up to answers, not surprises</h2>
              <p className="lp-sub lp-left">
                Guarda scans every hour overnight. The moment something new appears — a leaked key,
                an exposed staging server, a dropped security header — you get a WhatsApp message
                with the finding and the fix. <strong>Before your first coffee.</strong>
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
        </FadeInSection>
      </section>

      {/* ── Enterprise close ── */}
      <section className="lp-section">
        <FadeInSection>
          <h2 className="lp-h2">The deal is on the line. Your security posture decides.</h2>
          <p className="lp-sub">
            Your first enterprise customer sends a 40-question security review. Most SaaS founders
            fail it — not because the product is insecure, but because nobody ever looked at the
            external posture. <strong>Guarda gives you a professional report you hand straight to
            the prospect.</strong>
          </p>
          <p className="lp-sub" style={{ fontWeight: 700, color: "var(--accent-2)" }}>
            One enterprise deal you close because of that report pays for years of Guarda.
          </p>
        </FadeInSection>
      </section>

      {/* ── Why Guarda vs. competitors ── */}
      <section className="lp-section lp-band">
        <FadeInSection>
          <h2 className="lp-h2">Built for the founder who ships. Not the auditor who reports.</h2>
          <p className="lp-sub">
            The tools that do this today — Intruder, Detectify, Tenable — cost $3,000+/yr, need a
            security engineer to operate, and were built for compliance audits. <strong>Guarda is
            self-serve, plain English, and built for founders who are closing deals.</strong>
          </p>
        </FadeInSection>
        <FadeInSection delay={200}>
          <div className="lp-compare">
            <div className="lp-compare-col lp-compare-them">
              <div className="lp-compare-head">Traditional tools</div>
              <ul>
                <li>Weeks to deploy</li>
                <li>Security engineer required</li>
                <li>CVSS scores nobody reads</li>
                <li>$3,000+/yr</li>
              </ul>
            </div>
            <div className="lp-compare-col lp-compare-us">
              <div className="lp-compare-head">Guarda</div>
              <ul>
                <li>Results in 40 seconds</li>
                <li>Built for non-technical founders</li>
                <li>Plain English, one action each</li>
                <li>Fraction of the cost</li>
              </ul>
            </div>
          </div>
        </FadeInSection>
      </section>

      {/* ── Final CTA ── */}
      <section className="lp-final">
        <FadeInSection>
          <h2>
            Stop guessing. Start knowing.
            <br />
            <span className="lp-grad">Book your live demo today.</span>
          </h2>
          <div className="lp-demo">
            <button className="btn btn-hero btn-glow" onClick={() => setDemoOpen(true)}>
              Book a demo →
            </button>
            <div className="lp-demo-note">
              A 20-minute call. We&apos;ll scan your domain live and walk you through the report.
              No commitment. No credit card.
            </div>
          </div>
        </FadeInSection>
      </section>

      <BookDemoModal open={demoOpen} onClose={() => setDemoOpen(false)} />

      <footer className="lp-footer">
        <span>Guarda — We watch. We detect. We guide.</span>
        <span className="muted">Only scan assets you own or are authorized to test.</span>
      </footer>
    </div>
  );
}
