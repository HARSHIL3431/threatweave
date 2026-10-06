"use client";

import { Database, Settings, FileText, Share2 } from "lucide-react";
import { EyebrowBadge } from "@/components/brand/eyebrow-badge";
import { TwoToneHeading } from "@/components/brand/two-tone-heading";
import { IconTile } from "@/components/ui/icon-tile";
import { useState } from "react";

const cards = [
  { n: "01", accent: "var(--brand)", icon: <Database size={20} />, title: "Anomaly Detection", body: "Detect statistically unusual network behavior using a validated Isolation Forest model trained on CICIDS2017." },
  { n: "02", accent: "var(--blue)", icon: <Settings size={20} />, title: "Security Analytics", body: "Visualize detection activity, anomaly trends, and threat patterns across your network in real time." },
  { n: "03", accent: "var(--green)", icon: <FileText size={20} />, title: "Incident Intelligence", body: "Generate AI-powered incident analysis with attack context, evidence, and actionable recommendations." },
  { n: "04", accent: "var(--purple)", icon: <Share2 size={20} />, title: "MITRE ATT&CK Grounding", body: "Automatically map detected anomalies to MITRE ATT&CK techniques with context-aware explanations." },
];

export function Capabilities() {
  const [hover, setHover] = useState<number | null>(null);
  return (
    <section id="features" className="mx-auto max-w-[1360px] px-6 py-16">
      <EyebrowBadge>PLATFORM CAPABILITIES</EyebrowBadge>
      <TwoToneHeading lead="A Complete System for" accent="Modern Security Operations" className="mt-4 text-[44px]" />
      <p className="mt-3 max-w-2xl" style={{ color: "var(--text-muted)" }}>
        From detection to intelligence, THREATWEAVE provides everything you need to analyze, understand, and respond to network threats.
      </p>
      <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((c, i) => {
          const active = hover === i || (hover === null && i === 0);
          return (
            <div key={c.n}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
              className="rounded-2xl border p-6 transition-shadow"
              style={{ background: "var(--surface)", borderColor: active ? c.accent : "var(--border)", boxShadow: active ? `0 0 20px color-mix(in srgb, ${c.accent} 30%, transparent)` : "var(--card-shadow)" }}>
              <div className="font-mono text-xs" style={{ color: "var(--text-subtle)" }}>{c.n}</div>
              <div className="mt-3"><IconTile color={c.accent}>{c.icon}</IconTile></div>
              <h3 className="mt-4 text-lg font-bold" style={{ color: "var(--text)" }}>{c.title}</h3>
              <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>{c.body}</p>
              <a href="#" className="mt-4 inline-block text-sm font-semibold" style={{ color: c.accent }}>Learn more →</a>
            </div>
          );
        })}
      </div>
    </section>
  );
}
