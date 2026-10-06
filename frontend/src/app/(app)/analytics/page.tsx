"use client";

import Link from "next/link";
import { useState } from "react";
import { KpiCard } from "@/components/app/kpi-card";
import { DetectionsTable } from "@/components/app/detections-table";
import { TrendChart, DonutChart } from "@/components/charts/charts";
import { MOCK_DETECTIONS, MOCK_KPIS, SAMPLE_TREND, SAMPLE_SEVERITY_DONUT, SAMPLE_TOP_IPS } from "@/lib/data/detections";
import { Activity, AlertTriangle, ShieldAlert, Database, FileText, Shield, Search, Lightbulb, Download } from "lucide-react";

const REPORT_SECTIONS = [
  { icon: <FileText size={17} />, title: "Incident Overview", caption: "Summary of detected anomalies and key findings." },
  { icon: <Search size={17} />, title: "Attack Techniques", caption: "Mapped MITRE ATT&CK techniques with context." },
  { icon: <Activity size={17} />, title: "Evidence & Analysis", caption: "Supporting data, feature importance, and traffic patterns." },
  { icon: <Shield size={17} />, title: "Risk Assessment", caption: "Impact analysis and severity classification." },
  { icon: <Lightbulb size={17} />, title: "Recommended Actions", caption: "Step-by-step mitigation and response actions." },
];

const TABS = ["Incident Summary", "MITRE Analysis", "Evidence", "Recommendations"];

export default function Analytics() {
  const [tab, setTab] = useState(0);
  const [sel, setSel] = useState(0);
  const exportPdf = async () => {
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text("THREATWEAVE Incident Report", 20, 20);
    doc.setFontSize(11);
    TABS.forEach((t, i) => doc.text(`${t}: included`, 20, 34 + i * 8));
    doc.text(`Total Flows: ${MOCK_KPIS.networkFlows}   Anomalies: ${MOCK_KPIS.detectedAnomalies}   Critical: ${MOCK_KPIS.criticalThreats}`, 20, 72);
    doc.save("incident-report.pdf");
  };
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_350px]">
      <div className="space-y-6">
        <div>
          <h1 className="text-[28px] font-bold" style={{ color: "var(--text)" }}>Analytics &amp; Incident Report</h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Explore trends, analyze attack patterns, and generate comprehensive incident reports.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard label="Total Flows" value={MOCK_KPIS.networkFlows} delta="↑ 12.4% vs last week" accent="red" sparkColor="var(--brand)" spark={[3, 5, 4, 8, 6, 9, 7]} icon={<Database size={18} />} />
          <KpiCard label="Detected Anomalies" value={String(MOCK_KPIS.detectedAnomalies)} delta="↑ 8.1% vs last week" accent="red" sparkColor="var(--brand)" spark={[2, 4, 3, 7, 5, 8, 6]} icon={<AlertTriangle size={18} />} />
          <KpiCard label="Critical Threats" value={String(MOCK_KPIS.criticalThreats)} delta="↑ 3.2% vs last week" accent="red" sparkColor="var(--brand)" spark={[1, 3, 2, 5, 4, 6, 5]} icon={<ShieldAlert size={18} />} />
          <KpiCard label="Model Accuracy" value={MOCK_KPIS.modelAccuracy} delta="↑ 2.1% vs last week" accent="green" sparkColor="var(--green)" spark={[5, 6, 6, 7, 8, 8, 9]} icon={<Activity size={18} />} />
        </div>
        <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr_1fr]">
          <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <div className="flex items-center justify-between">
              <h2 className="font-bold" style={{ color: "var(--text)" }}>Anomaly Trend</h2>
              <span className="rounded-full border px-3 py-1 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>Last 7 days</span>
            </div>
            <TrendChart data={SAMPLE_TREND} yMax={80} />
          </div>
          <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Attack Type Distribution</h2>
            <DonutChart data={SAMPLE_SEVERITY_DONUT.map((d) => ({ label: d.label, pct: d.pct, color: d.color }))} centerLabel="Anomalies" centerValue={String(MOCK_KPIS.detectedAnomalies)} />
          </div>
          <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <div className="flex items-center justify-between">
              <h2 className="font-bold" style={{ color: "var(--text)" }}>Top Source IPs</h2>
              <Link href="/analytics" className="text-sm font-semibold" style={{ color: "var(--brand)" }}>View All →</Link>
            </div>
            <div className="mt-4 space-y-3">
              {SAMPLE_TOP_IPS.map((ip, i) => (
                <div key={ip.ip}>
                  <div className="flex justify-between text-[11px]"><span className="font-mono" style={{ color: "var(--text)" }}>{ip.ip}</span><span style={{ color: "var(--text-muted)" }}>{ip.count}</span></div>
                  <div className="h-1.5 rounded-full" style={{ background: "color-mix(in srgb, var(--text-subtle) 18%, transparent)" }}>
                    <div className="h-1.5 rounded-full" style={{ width: `${75 - i * 13}%`, background: i < 3 ? "var(--brand)" : "var(--text-subtle)" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="font-bold" style={{ color: "var(--text)" }}>Recent Detections</h2>
          <div className="mt-4"><DetectionsTable rows={MOCK_DETECTIONS} /></div>
        </div>
      </div>
      <aside className="space-y-4">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><FileText size={20} /></span>
            <div>
              <h3 className="font-bold" style={{ color: "var(--text)" }}>Generate Incident Report</h3>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>Create a comprehensive security incident report with AI-generated analysis and MITRE context.</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {TABS.map((t, i) => (
              <button key={t} onClick={() => setTab(i)} className="rounded-full border px-3 py-1 text-[12px] font-semibold"
                style={tab === i ? { background: "var(--brand)", borderColor: "var(--brand)", color: "#fff" } : { borderColor: "var(--border)", color: "var(--text-muted)" }}>
                {t}
              </button>
            ))}
          </div>
          <div className="mt-4 divide-y" style={{ borderColor: "var(--border)" }}>
            {REPORT_SECTIONS.map((s, i) => (
              <button key={s.title} onClick={() => setSel(i)} className="flex w-full items-start gap-3 py-3 text-left">
                <span style={{ color: sel === i ? "var(--brand)" : "var(--text-subtle)" }}>{s.icon}</span>
                <span>
                  <span className="block text-sm font-bold" style={{ color: "var(--text)" }}>{s.title}</span>
                  <span className="block text-xs" style={{ color: "var(--text-muted)" }}>{s.caption}</span>
                </span>
              </button>
            ))}
          </div>
          <button onClick={exportPdf} className="mt-4 flex w-full items-center justify-center gap-2 rounded-[10px] px-5 py-2.5 text-sm font-semibold text-white"
            style={{ backgroundImage: "linear-gradient(to bottom, var(--brand-grad-from), var(--brand-grad-to))", boxShadow: "var(--active-glow)" }}>
            <Download size={15} /> Export Incident Report (PDF)
          </button>
        </div>
      </aside>
    </div>
  );
}
