"use client";

import { useState } from "react";
import { Database, Settings, BarChart3, AlertTriangle, Shield, Search, FileText, ArrowRight, Globe, Network, Users } from "lucide-react";
import { EyebrowBadge } from "@/components/brand/eyebrow-badge";
import { TwoToneHeading } from "@/components/brand/two-tone-heading";
import { StepCard } from "@/components/ui/step-card";
import { STAGE_DEFS } from "@/lib/data/demoFlows";

const ICONS = [
  <Database key="a" size={18} />, <Settings key="b" size={18} />, <BarChart3 key="c" size={18} />, <AlertTriangle key="d" size={18} />,
  <Shield key="e" size={18} />, <Search key="f" size={18} />, <FileText key="g" size={18} />,
];

const DETAILS = [
  {
    tag: "STEP 01", title: "Raw Network Flow",
    body: "Network traffic data with 60 CICIDS2017 features including flow statistics, packet information, and temporal features.",
    cards: [
      { icon: <BarChart3 size={16} />, title: "60 Features", caption: "CICIDS2017 feature set" },
      { icon: <Network size={16} />, title: "Real Network Traffic", caption: "Bidirectional flow data" },
      { icon: <Users size={16} />, title: "Multiple Attack Types", caption: "Normal, DoS, PortScan, Web, Infiltration" },
    ],
  },
  {
    tag: "STEP 02", title: "Preprocessing",
    body: "Raw flows are cleaned, zero-duration cases are clipped to one microsecond, log1p transforms are applied, and the exact 60-feature contract is enforced.",
    cards: [
      { icon: <Settings size={16} />, title: "Zero-Duration Handling", caption: "Duration clipped, rates recomputed" },
      { icon: <BarChart3 size={16} />, title: "Log Transformations", caption: "log1p and signed-log" },
      { icon: <Network size={16} />, title: "Feature Ordering", caption: "Frozen E2 contract" },
    ],
  },
  {
    tag: "STEP 03", title: "Anomaly Detection",
    body: "The frozen E2 Isolation Forest scores each validated flow on the 60 engineered features, comparing behavior against normal traffic.",
    cards: [
      { icon: <BarChart3 size={16} />, title: "Isolation Forest", caption: "Experiment with_port (E2)" },
      { icon: <Network size={16} />, title: "60 Features", caption: "Validated contract" },
      { icon: <Shield size={16} />, title: "Frozen Model", caption: "No retraining at inference" },
    ],
  },
  {
    tag: "STEP 04", title: "Anomaly Score",
    body: "A numeric anomaly score between 0 and 1 is compared against the active frozen operating-point threshold to decide malicious or benign.",
    cards: [
      { icon: <AlertTriangle size={16} />, title: "OP-A Threshold", caption: "0.521919 frozen" },
      { icon: <BarChart3 size={16} />, title: "Score Semantics", caption: "Higher means more anomalous" },
      { icon: <Shield size={16} />, title: "Decision", caption: "Above threshold = anomaly" },
    ],
  },
  {
    tag: "STEP 05", title: "Severity Classification",
    body: "The score maps to a risk-based severity level from Informational through Critical, with an explicit placeholder calibration note.",
    cards: [
      { icon: <Shield size={16} />, title: "Info → Critical", caption: "Risk-based bands" },
      { icon: <AlertTriangle size={16} />, title: "Placeholder Calibration", caption: "Not a validated risk model" },
      { icon: <BarChart3 size={16} />, title: "Thresholds", caption: "0.80 critical, 0.65 high" },
    ],
  },
  {
    tag: "STEP 06", title: "Attack Context",
    body: "Detected anomalies are positioned for MITRE ATT&CK technique mapping with context-aware explanations and retrieval hooks.",
    cards: [
      { icon: <Search size={16} />, title: "MITRE Mapping", caption: "Technique IDs + names" },
      { icon: <Globe size={16} />, title: "RAG Retrieval", caption: "Context lookup hooks" },
      { icon: <Shield size={16} />, title: "Confidence", caption: "High / Medium / Low" },
    ],
  },
  {
    tag: "STEP 07", title: "Intelligence Report",
    body: "An analyst-ready incident report is generated with a summary, mapped techniques, evidence, risk assessment, and recommendations.",
    cards: [
      { icon: <FileText size={16} />, title: "LLM Analysis", caption: "Incident summary" },
      { icon: <Shield size={16} />, title: "Evidence", caption: "Flow + feature data" },
      { icon: <AlertTriangle size={16} />, title: "Recommendations", caption: "Actionable next steps" },
    ],
  },
];

export function HowItWorks() {
  const [active, setActive] = useState(0);
  const d = DETAILS[active];
  return (
    <section id="how-it-works" className="mx-auto max-w-[1360px] px-6 py-16">
      <EyebrowBadge>HOW IT WORKS</EyebrowBadge>
      <TwoToneHeading lead="From Network Traffic to" accent="Threat Intelligence" className="mt-4 text-[44px]" />
      <p className="mt-3 max-w-2xl" style={{ color: "var(--text-muted)" }}>
        Watch how a raw network flow is processed step by step to generate actionable security insights.
      </p>
      <div className="mt-10 flex items-stretch gap-2 overflow-x-auto pb-2">
        {STAGE_DEFS.map((s, i) => (
          <div key={s.n} className="flex items-center gap-2">
            <StepCard n={s.n} title={s.title} description={s.desc} icon={ICONS[i]} accent={s.accent} active={active === i} onClick={() => setActive(i)} />
            {i < 6 && (
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border" style={{ borderColor: "var(--border)", color: s.accent }}>
                <ArrowRight size={14} />
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="mt-8 grid gap-8 rounded-2xl border p-8 md:grid-cols-[1fr_1.2fr]" style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--card-shadow)" }}>
        <div className="relative h-64">
          {[0, 1, 2, 3, 4].map((layer) => (
            <div key={layer} className="absolute w-64 rounded-xl border p-4 font-mono text-[11px]"
              style={{
                top: layer * 10, left: layer * 18, transform: "perspective(800px) rotateY(-12deg)",
                background: "color-mix(in srgb, var(--surface) 80%, var(--text-subtle) 8%)",
                borderColor: "var(--border)", opacity: 1 - layer * 0.15,
              }}>
              <div className="text-[var(--text-muted)]">src_ip 192.168.1.124</div>
              <div className="text-[var(--text-muted)]">dst_ip 10.0.0.12</div>
              <div className="text-[var(--text-muted)]">protocol TCP</div>
              <div className="text-[var(--text-muted)]">src_port 49221</div>
              <div className="text-[var(--text-muted)]">dst_port 443</div>
              <div className="text-[var(--text-muted)]">duration 0.802</div>
              <div className="text-[var(--text-muted)]">packets 184</div>
              <div className="text-[var(--text-muted)]">bytes 12448</div>
            </div>
          ))}
        </div>
        <div>
          <span className="rounded px-2 py-0.5 font-mono text-[11px] font-bold" style={{ background: "var(--brand)", color: "#fff" }}>{d.tag}</span>
          <h3 className="mt-3 text-2xl font-bold" style={{ color: "var(--text)" }}>{d.title}</h3>
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>{d.body}</p>
          <div className="mt-5 grid grid-cols-3 gap-3">
            {d.cards.map((c) => (
              <div key={c.title} className="rounded-xl border p-3" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
                <span style={{ color: "var(--brand)" }}>{c.icon}</span>
                <div className="mt-2 text-[13px] font-bold" style={{ color: "var(--text)" }}>{c.title}</div>
                <div className="text-[11px]" style={{ color: "var(--text-subtle)" }}>{c.caption}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
