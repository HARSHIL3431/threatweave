"use client";

import Link from "next/link";
import { KpiCard } from "@/components/app/kpi-card";
import { DetectionsTable } from "@/components/app/detections-table";
import { TrendChart, DonutChart, BarList } from "@/components/charts/charts";
import { StatusPill } from "@/components/ui/status-pill";
import { MOCK_DETECTIONS, MOCK_KPIS, SAMPLE_ACTIVITY, SAMPLE_SEVERITY_DONUT, SAMPLE_ATTACK_TYPES } from "@/lib/data/detections";
import { Activity, AlertTriangle, ShieldAlert, Cpu } from "lucide-react";
import { useHealth } from "@/lib/use-health";

export default function Dashboard() {
  const { health, error } = useHealth();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-bold" style={{ color: "var(--text)" }}>Dashboard</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>Real-time overview of network activity and detected anomalies.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Network Flows" value={MOCK_KPIS.networkFlows} delta="↑ 12.4% vs last 24h" accent="red" sparkColor="var(--brand)" spark={[3, 5, 4, 8, 6, 9, 7]} icon={<Activity size={18} />} />
        <KpiCard label="Detected Anomalies" value={String(MOCK_KPIS.detectedAnomalies)} delta="↑ 8.1% vs last 24h" accent="red" sparkColor="var(--brand)" spark={[2, 4, 3, 7, 5, 8, 6]} icon={<AlertTriangle size={18} />} />
        <KpiCard label="Critical Threats" value={String(MOCK_KPIS.criticalThreats)} delta="↑ 3.2% vs last 24h" accent="red" sparkColor="var(--brand)" spark={[1, 3, 2, 5, 4, 6, 5]} icon={<ShieldAlert size={18} />} />
        <KpiCard label="Model Accuracy" value={MOCK_KPIS.modelAccuracy} delta="↑ 2.1% vs last week" accent="green" sparkColor="var(--green)" spark={[5, 6, 6, 7, 8, 8, 9]} icon={<Cpu size={18} />} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[2fr_1.4fr_1.4fr]">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between">
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Anomaly Activity</h2>
            <span className="rounded-full border px-3 py-1 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>Last 24 hours</span>
          </div>
          <TrendChart data={SAMPLE_ACTIVITY} yMax={40} />
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="font-bold" style={{ color: "var(--text)" }}>Severity Distribution</h2>
          <DonutChart data={SAMPLE_SEVERITY_DONUT.map((d) => ({ label: d.label, pct: d.pct, color: d.color }))} centerLabel="Anomalies" centerValue={String(MOCK_KPIS.detectedAnomalies)} />
          <div className="mt-2 space-y-1.5">
            {SAMPLE_SEVERITY_DONUT.map((d) => (
              <div key={d.label} className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: d.color }} />{d.label}</span>
                <span className="font-mono">{d.count} · {d.pct}%</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="font-bold" style={{ color: "var(--text)" }}>Attack Type Distribution</h2>
          <div className="mt-4"><BarList items={SAMPLE_ATTACK_TYPES} /></div>
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-[2.4fr_1fr]">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between">
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Recent Detections</h2>
            <Link href="/analytics" className="text-sm font-semibold" style={{ color: "var(--brand)" }}>View All →</Link>
          </div>
          <div className="mt-4"><DetectionsTable rows={MOCK_DETECTIONS.slice(0, 4)} /></div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="font-bold" style={{ color: "var(--text)" }}>System Status</h2>
          <div className="mt-4 space-y-3 text-sm">
            {[
              { label: "ML Model", value: health ? (health.model_status === "ready" ? "Running" : "Not Ready") : error ? "Unreachable" : "…", ok: health?.model_status === "ready" },
              { label: "Data Pipeline", value: "Healthy", ok: true },
              { label: "API Services", value: health ? "Healthy" : error ? "Down" : "…", ok: !!health },
              { label: "Database", value: "Connected", ok: true },
              { label: "Last Updated", value: "2 min ago", ok: null },
            ].map((r) => (
              <div key={r.label} className="flex items-center justify-between">
                <span className="flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: r.ok === null ? "var(--text-subtle)" : r.ok ? "var(--green)" : "var(--brand)" }} />
                  {r.label}
                </span>
                <StatusPill label={r.value} tone={r.ok === null ? "neutral" : "green"} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
