"use client";

import { useEffect, useRef, useState, useCallback, ReactNode } from "react";

/* ── SVG icon definitions (line-art, single-path where possible) ── */

function LaptopIcon() {
  return (
    <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M20 20h80v50H20zM20 70l-10 12h100l-10-12M50 30h20M45 40h30M40 50h40"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function HackerIcon() {
  return (
    <svg viewBox="0 0 100 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M50 10C30 10 20 30 20 45v5c0 10 5 18 12 23l-7 30h50l-7-30c7-5 12-13 12-23v-5c0-15-10-35-30-35zM35 50a4 4 0 108 0 4 4 0 00-8 0M57 50a4 4 0 108 0 4 4 0 00-8 0M40 65c5 5 15 5 20 0M15 35c-5-15 5-30 20-32M85 35c5-15-5-30-20-32"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FounderIcon() {
  return (
    <svg viewBox="0 0 100 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M50 15a15 15 0 110 30 15 15 0 010-30M30 55c0-5 9-10 20-10s20 5 20 10v8H30zM30 63h40v20c0 8-9 15-20 15s-20-7-20-15zM42 75h16M50 75v10M35 55l-10 15M65 55l10 15"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 100 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M50 8L15 28v30c0 25 15 42 35 52 20-10 35-27 35-52V28zM38 58l10 10 18-22M50 8v102M15 28h70"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 80 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M20 42V30a20 20 0 0140 0v12M12 42h56v45H12zM40 60v15M40 60a5 5 0 100-10 5 5 0 000 10"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function BugIcon() {
  return (
    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M35 25a15 10 0 0130 0M50 35v45M30 50h40M25 35l-12-8M75 35l12-8M22 55l-14 5M78 55l14 5M25 75l-10 12M75 75l10 12M30 35c0 0-5 5-5 20s5 30 25 30 25-15 25-30-5-20-5-20z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M10 40S30 10 60 10s50 30 50 30-20 30-50 30S10 40 10 40zM60 25a15 15 0 110 30 15 15 0 010-30M60 33a7 7 0 110 14 7 7 0 010-14M5 40h10M105 40h10M60 5v8M60 67v8M25 15l5 6M90 15l-5 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ServerIcon() {
  return (
    <svg viewBox="0 0 80 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M10 10h60v28H10zM10 42h60v28H10zM10 74h60v28H10zM20 24h4M30 24h4M20 56h4M30 56h4M20 88h4M30 88h4M55 24a2 2 0 104 0 2 2 0 00-4 0M55 56a2 2 0 104 0 2 2 0 00-4 0M55 88a2 2 0 104 0 2 2 0 00-4 0M40 38v4M40 70v4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        className="svg-reveal-path"
        d="M35 15L10 40l25 25M85 15l25 25-25 25M50 10l20 60M5 40h5M110 40h5"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ── Layout: where each icon sits, its size, color ── */

interface IconPlacement {
  Icon: () => ReactNode;
  x: string; // CSS left
  y: string; // CSS top
  size: number; // px
  color: string;
  delay: number; // scroll-reveal stagger ms
}

const ICONS: IconPlacement[] = [
  { Icon: LaptopIcon, x: "8%", y: "5%", size: 110, color: "#7c5cff", delay: 0 },
  { Icon: HackerIcon, x: "82%", y: "8%", size: 90, color: "#06b6d4", delay: 100 },
  { Icon: ShieldIcon, x: "88%", y: "35%", size: 100, color: "#a78bfa", delay: 200 },
  { Icon: FounderIcon, x: "5%", y: "38%", size: 95, color: "#22d3ee", delay: 150 },
  { Icon: EyeIcon, x: "75%", y: "58%", size: 105, color: "#7c5cff", delay: 250 },
  { Icon: LockIcon, x: "10%", y: "62%", size: 80, color: "#06b6d4", delay: 300 },
  { Icon: BugIcon, x: "85%", y: "80%", size: 85, color: "#a78bfa", delay: 200 },
  { Icon: ServerIcon, x: "3%", y: "82%", size: 80, color: "#22d3ee", delay: 350 },
  { Icon: CodeIcon, x: "45%", y: "90%", size: 100, color: "#7c5cff", delay: 100 },
];

/* ── Single icon wrapper with IntersectionObserver reveal ── */

function RevealIcon({ Icon, x, y, size, color, delay }: IconPlacement) {
  const ref = useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = useState(false);
  const [hover, setHover] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={revealed ? "icon-revealed" : ""}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: size,
        height: size,
        color,
        opacity: revealed ? (hover ? 0.5 : 0.22) : 0,
        transform: revealed
          ? `scale(${hover ? 1.18 : 1})`
          : "scale(0.5)",
        transition: `opacity 1.2s ease ${delay}ms, transform 0.9s cubic-bezier(.34,1.56,.64,1) ${delay}ms, filter 0.3s ease`,
        pointerEvents: "auto",
        cursor: "default",
        filter: hover ? `drop-shadow(0 0 16px ${color}90)` : "none",
      }}
    >
      <Icon />
    </div>
  );
}

/* ── Floating dots for subtle ambiance ── */

interface Dot {
  x: number;
  y: number;
  size: number;
  color: string;
  duration: number;
  delayMs: number;
}

function makeAmbientDots(count: number): Dot[] {
  const colors = ["#7c5cff", "#06b6d4", "#a78bfa", "#22d3ee"];
  const dots: Dot[] = [];
  for (let i = 0; i < count; i++) {
    dots.push({
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: 2 + Math.random() * 3,
      color: colors[i % colors.length],
      duration: 4 + Math.random() * 6,
      delayMs: Math.random() * 5000,
    });
  }
  return dots;
}

/* ── Main component ── */

export default function ParticleField() {
  const [dots] = useState(() => makeAmbientDots(30));
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollY, setScrollY] = useState(0);

  const onScroll = useCallback(() => {
    setScrollY(window.scrollY);
  }, []);

  useEffect(() => {
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [onScroll]);

  const parallaxOffset = scrollY * 0.08;

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        overflow: "hidden",
      }}
    >
      {/* CSS for stroke-draw + pulse animations */}
      <style>{`
        .svg-reveal-path {
          stroke-dasharray: 1200;
          stroke-dashoffset: 1200;
          transition: stroke-dashoffset 2s ease;
        }
        .icon-revealed .svg-reveal-path {
          stroke-dashoffset: 0;
        }
        @keyframes float-y {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        .icon-revealed svg {
          animation: float-y 6s ease-in-out infinite;
        }
        @keyframes dot-pulse {
          0%, 100% { opacity: 0.15; transform: scale(1); }
          50% { opacity: 0.45; transform: scale(1.5); }
        }
      `}</style>

      {/* Ambient pulsing dots */}
      {dots.map((d, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${d.x}%`,
            top: `${d.y}%`,
            width: d.size,
            height: d.size,
            borderRadius: "50%",
            backgroundColor: d.color,
            animation: `dot-pulse ${d.duration}s ease-in-out ${d.delayMs}ms infinite`,
            transform: `translateY(${-parallaxOffset}px)`,
          }}
        />
      ))}

      {/* SVG icon collection */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `translateY(${-parallaxOffset}px)`,
        }}
      >
        {ICONS.map((icon, i) => (
          <RevealIcon key={i} {...icon} />
        ))}
      </div>
    </div>
  );
}
