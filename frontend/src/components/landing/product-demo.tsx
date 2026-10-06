"use client";

import { Play, Activity, LayoutGrid, FileCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IconTile } from "@/components/ui/icon-tile";

export function ProductDemo() {
  return (
    <section id="platform" className="mx-auto grid max-w-[1360px] gap-12 px-6 py-16 lg:grid-cols-[1fr_1.4fr_1fr]">
      <div>
        <span className="text-[11px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--brand)" }}>PRODUCT DEMO</span>
        <h2 className="mt-3 text-[44px] font-extrabold leading-[1.1] tracking-[-0.02em]">
          <span style={{ color: "var(--text)" }}>See THREATWEAVE</span><br />
          <span style={{ color: "var(--brand)" }}>in Action</span>
        </h2>
        <p className="mt-4 max-w-sm" style={{ color: "var(--text-muted)" }}>
          Watch a complete walkthrough of the platform, including real-time detection, analysis, MITRE ATT&amp;CK mapping, and AI-generated incident reports.
        </p>
        <div className="mt-8 space-y-5">
          {[
            { icon: <Activity size={18} />, t: "Real Detection Flow", c: "End-to-end detection pipeline with live results" },
            { icon: <LayoutGrid size={18} />, t: "MITRE ATT&CK Mapping", c: "Automatic technique mapping and context retrieval" },
            { icon: <FileCheck size={18} />, t: "AI-Generated Reports", c: "Detailed incident analysis and recommendations" },
          ].map((f) => (
            <div key={f.t} className="flex gap-3">
              <IconTile color="var(--brand)">{f.icon}</IconTile>
              <div>
                <div className="font-bold" style={{ color: "var(--text)" }}>{f.t}</div>
                <div className="text-sm" style={{ color: "var(--text-muted)" }}>{f.c}</div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-8"><Button>▶ Watch Full Demo</Button></div>
      </div>
      <div className="relative flex items-center justify-center">
        <div className="w-full max-w-[720px] rounded-[26px] border p-3" style={{ background: "#C9CED6", borderColor: "var(--border)" }}>
          <div className="overflow-hidden rounded-[18px] border" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
            <div className="flex h-[300px] items-center justify-center text-sm" style={{ color: "var(--text-subtle)" }}>
              Dashboard preview
            </div>
          </div>
        </div>
        <button aria-label="Play demo" className="absolute grid h-16 w-16 place-items-center rounded-full bg-white shadow-xl">
          <Play size={26} style={{ color: "var(--brand)" }} fill="currentColor" />
        </button>
      </div>
      <div className="space-y-5">
        <p className="font-hand text-2xl" style={{ color: "var(--brand)", fontFamily: "var(--font-caveat), cursive" }}>
          See the platform in real time
        </p>
        <svg width="80" height="60" viewBox="0 0 80 60" aria-hidden>
          <path d="M70 5 Q 30 10 20 50" fill="none" stroke="var(--brand)" strokeWidth="2" strokeLinecap="round" />
          <path d="M14 44 L 20 52 L 27 44" fill="none" stroke="var(--brand)" strokeWidth="2" strokeLinecap="round" />
        </svg>
        {[
          { t: "Live Detection", c: "Real network traffic analysis" },
          { t: "Interactive Dashboard", c: "Explore detections and insights" },
          { t: "Complete Workflow", c: "From detection to report" },
        ].map((c) => (
          <div key={c.t} className="rounded-xl border p-4" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <div className="font-bold" style={{ color: "var(--text)" }}>{c.t}</div>
            <div className="text-sm" style={{ color: "var(--text-muted)" }}>{c.c}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
