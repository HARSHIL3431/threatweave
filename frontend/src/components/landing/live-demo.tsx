"use client";

import { useEffect, useRef, useState } from "react";
import { Database, Settings, BarChart3, AlertTriangle, Shield, Search, FileText, FileCheck } from "lucide-react";
import { EyebrowBadge } from "@/components/brand/eyebrow-badge";
import { TwoToneHeading } from "@/components/brand/two-tone-heading";
import { DEMO_FLOWS, DEMO_STEP_DEFS } from "@/lib/data/demoFlows";

const ICONS = [
  <Database key="a" size={18} />, <Settings key="b" size={18} />, <BarChart3 key="c" size={18} />, <AlertTriangle key="d" size={18} />,
  <Shield key="e" size={18} />, <Search key="f" size={18} />, <FileText key="g" size={18} />,
];

const TILE_COLORS = ["var(--brand)", "var(--blue)", "var(--green)", "var(--amber)", "var(--brand)", "var(--brand)", "var(--indigo)"];

export function LiveDemo() {
  const [flow, setFlow] = useState(0);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!playing) return;
    timer.current = setInterval(() => setStep((s) => (s + 1) % 7), 2500);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [playing]);

  const stage = DEMO_FLOWS[flow].stages[step];

  return (
    <section id="demo" className="mx-auto max-w-[1360px] px-6 py-16">
      <EyebrowBadge>LIVE INTERACTIVE DEMO</EyebrowBadge>
      <TwoToneHeading lead="Explore the Detection" accent="Pipeline" className="mt-4 text-[44px]" />
      <p className="mt-3 max-w-2xl" style={{ color: "var(--text-muted)" }}>
        Select a sample flow and watch how it is processed through our AI-powered detection pipeline.
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>Select Sample Flow</span>
          {DEMO_FLOWS.map((f, i) => (
            <button key={f.label} onClick={() => { setFlow(i); setStep(0); }}
              className="rounded-full border px-4 py-1.5 text-[13px] font-semibold transition-colors"
              style={flow === i
                ? { background: "var(--brand)", color: "#fff", borderColor: "var(--brand)" }
                : { borderColor: "var(--border)", color: "var(--text-muted)", background: "var(--surface)" }}>
              {f.label}
            </button>
          ))}
        </div>
        <button onClick={() => setPlaying((p) => !p)}
          className="rounded-[10px] border px-4 py-2 text-sm font-semibold"
          style={{ borderColor: "var(--brand)", color: "var(--brand)", background: playing ? "var(--brand-soft)" : "transparent" }}>
          {playing ? "Pause Demo" : "Resume Demo"}
        </button>
      </div>
      <div className="mt-8 flex gap-2 overflow-x-auto pb-2">
        {DEMO_STEP_DEFS.map((s, i) => (
          <button key={s.n} onClick={() => { setStep(i); setPlaying(false); }}
            className="flex min-w-[170px] max-w-[210px] flex-col items-start gap-2 rounded-2xl border p-4 text-left"
            style={{ background: "var(--surface)", borderColor: step === i ? "var(--brand)" : "var(--border)", boxShadow: step === i ? "var(--active-glow)" : "var(--card-shadow)" }}>
            <span className="rounded-md px-1.5 py-0.5 font-mono text-[11px] font-bold" style={{ background: `color-mix(in srgb, ${s.accent} 15%, transparent)`, color: s.accent }}>{s.n}</span>
            <span style={{ color: s.accent }}>{ICONS[i]}</span>
            <span className="text-sm font-bold" style={{ color: "var(--text)" }}>{s.title}</span>
            <span className="text-[12px]" style={{ color: "var(--text-muted)" }}>{s.desc}</span>
          </button>
        ))}
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2 text-sm font-bold" style={{ color: "var(--text)" }}>
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--brand)" }} /> Live Pipeline Output
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {DEMO_FLOWS[flow].stages.map((s, i) => (
              <button key={s.name} onClick={() => { setStep(i); setPlaying(false); }}
                className="rounded-full border px-3 py-1 text-[12px] font-semibold"
                style={step === i ? { background: "var(--brand-soft)", borderColor: "var(--brand)", color: "var(--brand)" } : { borderColor: "var(--border)", color: "var(--text-muted)" }}>
                {s.name === "ML Analysis" ? "ML Analysis" : s.name}
              </button>
            ))}
          </div>
          <pre className="mt-4 overflow-x-auto rounded-xl border p-4 font-mono text-[12.5px] leading-relaxed"
            style={{ background: "#0A1120", borderColor: "var(--border)", color: "#C7D2E4" }}>
            <code>{stage.body.split("\n").map((l, i) => `${String(i + 1).padStart(2, " ")}  ${l}`).join("\n")}</code>
          </pre>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "#0A1120", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--brand)" }} /> Pipeline Visualization
          </div>
          <div className="mt-6 flex items-center gap-3 overflow-x-auto">
            <span className="whitespace-nowrap text-[11px] uppercase tracking-wider" style={{ color: "#6F7B93" }}>Network Flow</span>
            {DEMO_STEP_DEFS.map((s, i) => (
              <div key={s.n} className="flex items-center gap-2">
                <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border text-center text-[9px] font-bold"
                  style={{
                    borderColor: step === i ? TILE_COLORS[i] : "rgba(255,255,255,0.1)",
                    color: TILE_COLORS[i],
                    background: step === i ? `color-mix(in srgb, ${TILE_COLORS[i]} 18%, transparent)` : "rgba(255,255,255,0.04)",
                    boxShadow: step === i ? `0 0 16px ${TILE_COLORS[i]}55` : "none",
                  }}>
                  {s.title.split(" ")[0]}
                </div>
                {i < 6 && <span className="h-1.5 w-1.5 rounded-full" style={{ background: TILE_COLORS[i] }} />}
              </div>
            ))}
            <div className="ml-2 flex h-16 w-32 shrink-0 flex-col justify-center gap-1.5 rounded-xl border border-white/10 bg-white/5 p-3">
              <FileCheck size={16} className="text-white/70" />
              <div className="h-1 w-16 rounded bg-white/20" />
              <div className="h-1 w-10 rounded bg-white/10" />
              <div className="text-[9px] uppercase tracking-wider text-white/50">Security Intelligence</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
