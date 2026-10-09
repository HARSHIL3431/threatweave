"use client";

import Link from "next/link";
import { KpiCard } from "@/components/app/kpi-card";
import { SessionDetectionsTable } from "@/components/app/session-table";
import { TrendChart, DonutChart } from "@/components/charts/charts";
import { Activity, AlertTriangle, ShieldAlert, Gauge, Download } from "lucide-react";
import { useHealth } from "@/lib/use-health";
import {
  SESSION_SCOPE_NOTE,
  clearSessionDetections,
  sessionStats,
  useSessionDetections,
} from "@/lib/session-store";

const SEV_COLORS: Record<string, string> = {
  critical: "var(--brand)",
  high: "var(--orange)",
  medium: "var(--amber)",
  low: "#D9C46A",
  info: "var(--text-subtle)",
};

export default function Analytics() {
  const { health } = useHealth();
  const session = useSessionDetections();
  const stats = sessionStats(session);

  const trend = session
    .slice()
    .reverse()
    .map((r, i) => ({ t: `#${i + 1}`, v: Number(r.detection.anomaly_score.toFixed(4)) }));
  const donut = Object.entries(stats.bySeverity).map(([label, count]) => ({
    label: label[0].toUpperCase() + label.slice(1),
    pct: Math.round((count / Math.max(1, stats.total)) * 100),
    color: SEV_COLORS[label] ?? "var(--text-subtle)",
  }));

  const exportPdf = async () => {
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text("THREATWEAVE Session Report", 20, 20);
    doc.setFontSize(10);
    doc.text("Source: live backend /detect responses recorded in this browser session.", 20, 28);
    doc.text(`Records: ${stats.total}   Anomalies: ${stats.anomalies}   Generated: ${new Date().toISOString()}`, 20, 35);
    let y = 45;
    for (const r of session) {
      if (y > 270) {
        doc.addPage();
        y = 20;
      }
      doc.text(
        `${r.request_id.slice(0, 8)}  score=${r.detection.anomaly_score.toFixed(4)}  thr=${r.detection.threshold.toFixed(4)}  ${r.detection.is_anomaly ? "ANOMALOUS" : "BENIGN"}  sev=${r.severity.level}`,
        20,
        y
      );
      y += 7;
    }
    doc.save("threatweave-session-report.pdf");
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_350px]">
      <div className="space-y-6">
        <div>
          <h1 className="text-[28px] font-bold" style={{ color: "var(--text)" }}>Analytics &amp; Incident Report</h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Aggregates derive from live session responses ({SESSION_SCOPE_NOTE}).
            The backend keeps no persisted history, so server-side trends do not exist.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard label="Flows Scored (session)" value={String(stats.total)} caption="Live responses, this browser" accent="red" sparkColor="var(--brand)" spark={stats.spark} icon={<Activity size={18} />} />
          <KpiCard label="Anomalies (session)" value={String(stats.anomalies)} caption="score ≥ threshold" accent="red" sparkColor="var(--brand)" spark={stats.spark} icon={<AlertTriangle size={18} />} />
          <KpiCard label="High / Critical (session)" value={String(stats.highCritical)} caption="placeholder severity bands" accent="red" sparkColor="var(--brand)" icon={<ShieldAlert size={18} />} />
          <KpiCard label="Active Threshold (live)" value={health?.active_threshold != null ? health.active_threshold.toFixed(4) : "…"} caption={health ? `${health.experiment_id} / ${health.active_operating_point}` : "loading model metadata"} accent="green" sparkColor="var(--green)" icon={<Gauge size={18} />} />
        </div>
        <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr_1fr]">
          <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <div className="flex items-center justify-between">
              <h2 className="font-bold" style={{ color: "var(--text)" }}>Session Scores</h2>
              <span className="rounded-full border px-3 py-1 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>Run order · this session</span>
            </div>
            {trend.length > 0 ? (
              <TrendChart data={trend} yMax={1} />
            ) : (
              <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>No session data yet. Scores from live runs will appear here in run order.</p>
            )}
          </div>
          <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Severity Mix</h2>
            {stats.total > 0 ? (
              <DonutChart data={donut} centerLabel="Session flows" centerValue={String(stats.total)} />
            ) : (
              <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>No session data yet.</p>
            )}
          </div>
          <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Top Source IPs</h2>
            <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Not available — detection requests carry flow features only, and the backend stores no history to aggregate.
            </p>
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between">
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Session Detections</h2>
            {session.length > 0 && (
              <button onClick={clearSessionDetections} className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                Clear session
              </button>
            )}
          </div>
          <div className="mt-4">
            {session.length > 0 ? (
              <SessionDetectionsTable rows={session} />
            ) : (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                No persisted detection history is available. Score a flow in <Link href="/reports" className="font-semibold" style={{ color: "var(--brand)" }}>Reports</Link> to record live responses here.
              </p>
            )}
          </div>
        </div>
      </div>
      <aside className="space-y-4">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h3 className="font-bold" style={{ color: "var(--text)" }}>Export Session Report</h3>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Client-side summary of the {stats.total} live backend response(s) in this browser session — not a server-generated incident report.
          </p>
          <button disabled={session.length === 0} onClick={exportPdf} className="mt-4 flex w-full items-center justify-center gap-2 rounded-[10px] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            style={{ backgroundImage: "linear-gradient(to bottom, var(--brand-grad-from), var(--brand-grad-to))", boxShadow: "var(--active-glow)" }}>
            <Download size={15} /> Export Session Report (PDF)
          </button>
          <p className="mt-2 text-[11px]" style={{ color: "var(--text-subtle)" }}>
            Authoritative backend PDFs are generated in <Link href="/reports" className="font-semibold" style={{ color: "var(--brand)" }}>Reports</Link>.
          </p>
        </div>
      </aside>
    </div>
  );
}
