"use client";

import { motion } from "framer-motion";
import { ArrowRight, PlayCircle, Database, Settings, Brain, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

function Globe() {
  const hotspots = [
    { x: 320, y: 120, r: 6 },
    { x: 130, y: 330, r: 5 },
    { x: 330, y: 260, r: 5 },
  ];
  return (
    <svg viewBox="0 0 520 480" className="h-full w-full" aria-hidden>
      <defs>
        <radialGradient id="globeGlow" cx="50%" cy="50%" r="50%">
          <stop offset="60%" stopColor="transparent" />
          <stop offset="100%" stopColor="rgba(59,140,255,0.25)" />
        </radialGradient>
        <pattern id="dots" width="7" height="7" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1.4" fill="#3B8CFF" opacity="0.85" />
        </pattern>
      </defs>
      <circle cx="260" cy="240" r="185" fill="url(#dots)" opacity="0.9" />
      <circle cx="260" cy="240" r="185" fill="url(#globeGlow)" />
      <circle cx="260" cy="240" r="185" fill="none" stroke="rgba(59,140,255,0.5)" strokeWidth="1" />
      <ellipse cx="260" cy="240" rx="185" ry="60" fill="none" stroke="rgba(59,140,255,0.3)" />
      <ellipse cx="260" cy="240" rx="60" ry="185" fill="none" stroke="rgba(59,140,255,0.2)" />
      {hotspots.map((h, i) => (
        <g key={i}>
          <motion.circle cx={h.x} cy={h.y} r={h.r} fill="var(--brand)"
            animate={{ opacity: [1, 0.4, 1] }} transition={{ repeat: Infinity, duration: 2, delay: i * 0.5 }} />
          <motion.circle cx={h.x} cy={h.y} r={h.r} fill="none" stroke="var(--brand)" strokeWidth="1.5"
            animate={{ r: [h.r, h.r + 18], opacity: [0.8, 0] }} transition={{ repeat: Infinity, duration: 2, delay: i * 0.5 }} />
        </g>
      ))}
      <path d="M320 120 Q 200 60 130 330" fill="none" stroke="var(--brand)" strokeWidth="1" opacity="0.6" />
      <path d="M320 120 Q 420 180 330 260" fill="none" stroke="var(--brand)" strokeWidth="1" opacity="0.6" />
      <path d="M130 330 Q 240 380 330 260" fill="none" stroke="var(--brand)" strokeWidth="1" opacity="0.4" />
    </svg>
  );
}

function FloatingCard({ title, subtitle, delay }: { title: string; subtitle: string; delay: number }) {
  return (
    <motion.div
      animate={{ y: [0, -10, 0] }}
      transition={{ repeat: Infinity, duration: 5, delay, ease: "easeInOut" }}
      className="w-52 rounded-xl border p-3 backdrop-blur"
      style={{ background: "color-mix(in srgb, var(--surface) 82%, transparent)", borderColor: "var(--border)", boxShadow: "var(--card-shadow)" }}
    >
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full" style={{ background: "var(--brand)" }} />
        <span className="text-sm font-bold" style={{ color: "var(--text)" }}>{title}</span>
      </div>
      <div className="mt-0.5 font-mono text-[11px]" style={{ color: "var(--text-muted)" }}>{subtitle}</div>
      <div className="mt-2 flex items-end gap-1">
        {[4, 8, 5, 12, 7, 14, 9].map((h, i) => (
          <span key={i} className="w-1.5 rounded-sm" style={{ height: h, background: "var(--brand)" }} />
        ))}
      </div>
    </motion.div>
  );
}

const stats = [
  { icon: <Database size={20} />, color: "var(--blue)", value: "2.83M+", label: "Network Flows Analyzed", caption: "CICIDS2017 Dataset" },
  { icon: <Settings size={20} />, color: "var(--purple)", value: "60", label: "Detection Features", caption: "Engineered & Validated" },
  { icon: <Brain size={20} />, color: "var(--brand)", value: "Isolation Forest", label: "Primary Detector", caption: "F1-validated Model (E2)" },
  { icon: <ShieldCheck size={20} />, color: "var(--green)", value: "MITRE ATT&CK", label: "Intelligence Framework", caption: "Context-Aware Analysis" },
];

export function Hero() {
  return (
    <section className="relative mx-auto max-w-[1360px] px-6 pt-16 pb-8">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold"
            style={{ color: "var(--green)", borderColor: "color-mix(in srgb, var(--green) 40%, transparent)", background: "color-mix(in srgb, var(--green) 10%, transparent)" }}>
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--green)", boxShadow: "0 0 8px var(--green)" }} />
            Detection Engine Operational
          </span>
          <h1 className="mt-5 text-[64px] font-extrabold leading-[1.05] tracking-[-0.02em]">
            <span className="block" style={{ color: "var(--text)" }}>Detect what</span>
            <span style={{ color: "var(--brand)" }}>doesn&rsquo;t belong.</span>
          </h1>
          <p className="mt-5 max-w-md text-[16px]" style={{ color: "var(--text-muted)" }}>
            Analyze network traffic with AI-powered anomaly detection, MITRE ATT&amp;CK context, and intelligent incident reports.
          </p>
          <div className="mt-7 flex items-center gap-3">
            <Link href="/dashboard"><Button>Open Dashboard <ArrowRight size={16} /></Button></Link>
            <Button variant="outline"><PlayCircle size={16} /> Watch Demo</Button>
          </div>
        </div>
        <div className="relative h-[480px]">
          <Globe />
          <div className="absolute right-0 top-2"><FloatingCard title="Port Scan Detected" subtitle="192.168.1.0/24" delay={0} /></div>
          <div className="absolute left-0 top-[45%]"><FloatingCard title="DDoS Attack" subtitle="High Volume Traffic" delay={1.2} /></div>
          <div className="absolute bottom-4 right-6"><FloatingCard title="Web Attack" subtitle="Suspicious Request" delay={2.1} /></div>
        </div>
      </div>
      <div className="mt-12 grid grid-cols-4 divide-x rounded-2xl border p-6" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col items-center gap-1 text-center">
            <span className="grid h-10 w-10 place-items-center rounded-full" style={{ background: `color-mix(in srgb, ${s.color} 12%, transparent)`, color: s.color }}>{s.icon}</span>
            <span className="text-xl font-extrabold" style={{ color: "var(--text)" }}>{s.value}</span>
            <span className="text-sm" style={{ color: "var(--text)" }}>{s.label}</span>
            <span className="text-xs" style={{ color: "var(--text-subtle)" }}>{s.caption}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
