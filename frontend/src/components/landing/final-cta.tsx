"use client";

import Link from "next/link";
import { Play, Shield, BarChart3, Zap } from "lucide-react";
import { EyebrowBadge } from "@/components/brand/eyebrow-badge";
import { TwoToneHeading } from "@/components/brand/two-tone-heading";
import { Button } from "@/components/ui/button";

export function FinalCta() {
  return (
    <section className="mx-auto max-w-[1360px] px-6 py-20 text-center">
      <EyebrowBadge>READY TO GET STARTED</EyebrowBadge>
      <TwoToneHeading lead="Turn Network Data into" accent="Actionable Security Intelligence" className="mx-auto mt-4 max-w-3xl text-[44px]" />
      <p className="mx-auto mt-4 max-w-xl" style={{ color: "var(--text-muted)" }}>
        Experience real-time detection, MITRE ATT&amp;CK mapping, and AI-powered analysis with THREATWEAVE.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/dashboard"><Button><Play size={16} /> Get Started</Button></Link>
        <Button variant="outline" onClick={() => window.dispatchEvent(new Event("threatweave:play-demo"))}>Watch Demo</Button>
      </div>
      <div className="mx-auto mt-12 grid max-w-3xl grid-cols-3 divide-x" style={{ borderColor: "var(--border)" }}>
        {[
          { icon: <Zap size={18} />, t: "Real-Time Detection", c: "Identify threats as they happen" },
          { icon: <Shield size={18} />, t: "AI-Powered Analysis", c: "From data to insights" },
          { icon: <BarChart3 size={18} />, t: "Actionable Reports", c: "Investigation-ready intelligence" },
        ].map((f) => (
          <div key={f.t} className="flex flex-col items-center gap-1 px-4">
            <span style={{ color: "var(--brand)" }}>{f.icon}</span>
            <span className="font-bold" style={{ color: "var(--text)" }}>{f.t}</span>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>{f.c}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
