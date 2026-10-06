"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { MOCK_DETECTIONS } from "@/lib/data/detections";
import { Gauge } from "@/components/charts/charts";
import { TechniqueChip } from "@/components/ui/technique-chip";
import { ConfidenceBadge } from "@/components/ui/confidence-badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, ChevronLeft, ChevronRight, Download, AlertTriangle, Shield, Layers, Sparkles, Lightbulb, ExternalLink } from "lucide-react";

export default function DetectionDetails() {
  const params = useParams();
  const router = useRouter();
  const id = String(params.id);
  const idx = Math.max(0, MOCK_DETECTIONS.findIndex((d) => d.id === id));
  const d = MOCK_DETECTIONS[idx] ?? MOCK_DETECTIONS[0];
  const prev = MOCK_DETECTIONS[(idx - 1 + MOCK_DETECTIONS.length) % MOCK_DETECTIONS.length];
  const next = MOCK_DETECTIONS[(idx + 1) % MOCK_DETECTIONS.length];

  const exportPdf = async () => {
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text("Security Incident Report", 20, 20);
    doc.setFontSize(11);
    doc.text(`Type: ${d.type}    Severity: ${d.severity}    Score: ${d.score}`, 20, 32);
    doc.text(`Source: ${d.srcIp}:${d.srcPort}    Destination: ${d.dstIp}:${d.dstPort}`, 20, 40);
    doc.text(`MITRE: ${d.mitre.primary.id} ${d.mitre.primary.name} (${d.mitre.primary.confidence} confidence)`, 20, 48);
    doc.text(doc.splitTextToSize(d.aiAnalysis || "No AI analysis available.", 170), 20, 60);
    doc.save(`incident-${d.id}.pdf`);
  };

  const maxFI = Math.max(...d.featureImportance.map((f) => f.value), 0.01);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" aria-label="Back" className="grid h-10 w-10 place-items-center rounded-[10px] border" style={{ borderColor: "var(--border)", color: "var(--text)" }}>
            <ArrowLeft size={17} />
          </Link>
          <div>
            <h1 className="text-[28px] font-bold" style={{ color: "var(--text)" }}>Detection Details</h1>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Detailed analysis, MITRE ATT&amp;CK mapping, and AI-generated insights for this network flow.</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push(`/detections/${prev.id}`)}><ChevronLeft size={15} /> Previous</Button>
          <Button variant="outline" onClick={() => router.push(`/detections/${next.id}`)}>Next <ChevronRight size={15} /></Button>
          <Button onClick={exportPdf}><Download size={15} /> Export Report (PDF)</Button>
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-[2fr_1fr_1fr_1fr]">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><AlertTriangle size={20} /></span>
            <div>
              <div className="font-bold" style={{ color: "var(--brand)" }}>Anomaly Detected</div>
              <span className="rounded px-1.5 py-0.5 text-[10px] font-bold text-white" style={{ background: "var(--brand)" }}>{d.severity} SEVERITY</span>
            </div>
          </div>
          <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>Anomalous network flow detected by Isolation Forest model</p>
          <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
            {Object.entries({
              "Detection Time": "Sep 20, 2026 14:23:06",
              "Source IP": d.srcIp,
              "Destination IP": d.dstIp,
              Protocol: d.protocol,
              "Source Port": String(d.srcPort),
              "Destination Port": String(d.dstPort),
            }).map(([k, v]) => (
              <div key={k}>
                <div style={{ color: "var(--text-subtle)" }}>{k}</div>
                <div className="font-mono font-semibold" style={{ color: "var(--text)" }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border p-5 text-center" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <Gauge value={d.score} />
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <span className="grid h-10 w-10 place-items-center rounded-xl" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><Shield size={20} /></span>
          <div className="mt-3 text-2xl font-extrabold" style={{ color: "var(--brand)" }}>{d.severity}</div>
          <div className="text-xs" style={{ color: "var(--text-subtle)" }}>Severity</div>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>High likelihood of malicious activity</p>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <span className="grid h-10 w-10 place-items-center rounded-xl" style={{ background: "color-mix(in srgb, var(--blue) 12%, transparent)", color: "var(--blue)" }}><Layers size={20} /></span>
          <div className="mt-3 font-mono text-2xl font-extrabold" style={{ color: "var(--text)" }}>{d.mitre.primary.id}</div>
          <div className="text-xs" style={{ color: "var(--text-subtle)" }}>Top MITRE Technique</div>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>{d.mitre.primary.name}</p>
          <div className="mt-2"><ConfidenceBadge level={d.mitre.primary.confidence} /></div>
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-4">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between">
            <h3 className="font-bold" style={{ color: "var(--text)" }}>Network Flow Data</h3>
            <button onClick={() => navigator.clipboard.writeText(JSON.stringify(d.flow, null, 2))} className="text-xs font-semibold" style={{ color: "var(--brand)" }}>Copy</button>
          </div>
          <pre className="mt-3 overflow-x-auto rounded-xl border p-3 font-mono text-[11px]" style={{ background: "color-mix(in srgb, var(--text-subtle) 8%, transparent)", borderColor: "var(--border)", color: "var(--text)" }}>
            {JSON.stringify(d.flow, null, 2)}
          </pre>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h3 className="font-bold" style={{ color: "var(--text)" }}>Feature Importance</h3>
          <div className="mt-3 space-y-2">
            {d.featureImportance.length === 0 && <p className="text-xs" style={{ color: "var(--text-subtle)" }}>SAMPLE: no feature attribution from backend.</p>}
            {d.featureImportance.map((f, i) => (
              <div key={f.name}>
                <div className="flex justify-between text-[11px]"><span style={{ color: "var(--text-muted)" }}>{f.name}</span><span className="font-mono" style={{ color: "var(--text)" }}>{f.value.toFixed(2)}</span></div>
                <div className="h-1.5 rounded-full" style={{ background: "color-mix(in srgb, var(--text-subtle) 18%, transparent)" }}>
                  <div className="h-1.5 rounded-full" style={{ width: `${(f.value / maxFI) * 100}%`, background: f.name === "Others" ? "var(--text-subtle)" : "var(--brand)", opacity: 1 - i * 0.09 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between">
            <h3 className="font-bold" style={{ color: "var(--text)" }}>MITRE ATT&amp;CK Context</h3>
            <ExternalLink size={14} style={{ color: "var(--text-subtle)" }} />
          </div>
          <div className="mt-3 flex items-center gap-2">
            <TechniqueChip id={d.mitre.primary.id} />
            <span className="text-sm font-bold" style={{ color: "var(--text)" }}>{d.mitre.primary.name}</span>
          </div>
          <div className="mt-1"><ConfidenceBadge level={d.mitre.primary.confidence} /></div>
          <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>{d.mitre.primary.description}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {d.mitre.related.map((t) => <TechniqueChip key={t.id} id={t.id} />)}
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h3 className="flex items-center gap-2 font-bold" style={{ color: "var(--text)" }}><Sparkles size={16} style={{ color: "var(--brand)" }} /> AI-Generated Analysis</h3>
          <p className="mt-3 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>{d.aiAnalysis}</p>
          <div className="mt-4 rounded-xl border p-3" style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--amber) 10%, transparent)" }}>
            <div className="flex items-center gap-2 text-sm font-bold" style={{ color: "var(--text)" }}><Lightbulb size={15} style={{ color: "var(--amber)" }} /> Recommended Actions</div>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs" style={{ color: "var(--brand)" }}>
              {d.recommendedActions.map((a) => <li key={a}>{a}</li>)}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
