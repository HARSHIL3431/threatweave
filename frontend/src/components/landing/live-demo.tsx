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
            className="flex min-w-[170px] max-w-[210px] flex-col items-start gap-2 rounded-2xl border p-4 text-left transition-shadow duration-300"
            style={{ background: "var(--surface)", borderColor: step === i ? s.accent : "var(--border)", boxShadow: step === i ? `0 0 0 1px ${s.accent}, 0 0 18px color-mix(in srgb, ${s.accent} 30%, transparent)` : "var(--card-shadow)" }}>
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
                style={step === i ? { background: `color-mix(in srgb, ${DEMO_STEP_DEFS[i].accent} 12%, transparent)`, borderColor: DEMO_STEP_DEFS[i].accent, color: DEMO_STEP_DEFS[i].accent } : { borderColor: "var(--border)", color: "var(--text-muted)" }}>
                {s.name === "ML Analysis" ? "ML Analysis" : s.name}
              </button>
            ))}
          </div>
          <pre className="mt-4 overflow-x-auto rounded-xl border p-4 font-mono text-[12.5px] leading-relaxed"
            style={{ background: "#0A1120", borderColor: "var(--border)", color: "#C7D2E4" }}>
            <code>{stage.body.split("\n").map((l, i) => `${String(i + 1).padStart(2, " ")}  ${l}`).join("\n")}</code>
          </pre>
        </div>
        <div className="flex flex-col rounded-2xl border p-5" style={{ background: "#0A1120", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--brand)" }} /> Pipeline Visualization
          </div>
          <div className="flex flex-1 items-center py-6">
            <div className="flex w-full flex-col items-center gap-6">
              {[DEMO_STEP_DEFS.slice(0, 4), DEMO_STEP_DEFS.slice(4)].map((row, r) => (
                <div key={r} className="flex w-full items-start overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                  {r === 0 && (
                    <div className="flex h-12 w-[86px] shrink-0 items-center justify-center px-1 text-center">
                      <span className="whitespace-nowrap text-[10px] uppercase tracking-wider" style={{ color: "#6F7B93" }}>Network Flow</span>
                    </div>
                  )}
                  {row.map((s, j) => {
                    const i = r === 0 ? j : j + 4;
                    return (
                      <div key={s.n} className="flex min-w-0 flex-1 items-start">
                        {j > 0 && (
                          <span className="relative mx-1 mt-6 h-px min-w-2 flex-1" style={{ background: "rgba(255,255,255,0.18)" }}>
                            <span className="absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ background: s.accent }} />
                          </span>
                        )}
                        <div className="flex w-[86px] min-w-[86px] shrink-0 flex-col items-center gap-3 px-1 text-center sm:w-[104px] sm:min-w-[104px]">
                          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border transition-shadow duration-300"
                            style={{
                              borderColor: step === i ? s.accent : "rgba(255,255,255,0.1)",
                              color: s.accent,
                              background: step === i ? `color-mix(in srgb, ${s.accent} 18%, transparent)` : "rgba(255,255,255,0.04)",
                              boxShadow: step === i ? `0 0 16px ${s.accent}55` : "none",
                            }}>
                            {ICONS[i]}
                          </div>
                          <div className="text-[9px] font-bold uppercase tracking-wider" style={{ color: s.accent }}>{s.n}</div>
                          <div className="text-[10px] font-bold leading-tight text-white/90 break-words">{s.title}</div>
                        </div>
                      </div>
                    );
                  })}
                  {r === 1 && (
                    <span className="relative mx-1 mt-6 h-px min-w-2 flex-1" style={{ background: "rgba(255,255,255,0.18)" }}>
                      <span className="absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ background: DEMO_STEP_DEFS[6].accent }} />
                    </span>
                  )}
                  {r === 1 && (
                    <div className="flex w-[110px] shrink-0 flex-col justify-center gap-1.5 self-center rounded-xl border border-white/10 bg-white/5 p-3">
                      <FileCheck size={16} className="text-white/70" />
                      <div className="h-1 w-16 rounded bg-white/20" />
                      <div className="h-1 w-10 rounded bg-white/10" />
                      <div className="text-[9px] uppercase tracking-wider text-white/50">Security Intelligence</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
