"use client";

import Link from "next/link";
import { KpiCard } from "@/components/app/kpi-card";
import { SessionDetectionsTable } from "@/components/app/session-table";
import { TrendChart, DonutChart } from "@/components/charts/charts";
import { StatusPill } from "@/components/ui/status-pill";
import { Activity, AlertTriangle, ShieldAlert, Gauge } from "lucide-react";
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

function EmptyState({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="grid place-items-center rounded-xl border py-8 text-center" style={{ borderColor: "var(--border)" }}>
      <div>
        <div className="text-sm font-bold" style={{ color: "var(--text)" }}>{title}</div>
        <p className="mx-auto mt-1 max-w-sm text-xs" style={{ color: "var(--text-muted)" }}>{body}</p>
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  );
}

const runLiveCta = (
  <Link href="/reports" className="rounded-[10px] px-4 py-1.5 text-xs font-semibold text-white"
    style={{ backgroundImage: "linear-gradient(to bottom, var(--brand-grad-from), var(--brand-grad-to))" }}>
    Run a live analysis
  </Link>
);

export default function Dashboard() {
  const { health, error } = useHealth();
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-bold" style={{ color: "var(--text)" }}>Dashboard</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          System status and model metadata are live. Activity metrics reflect {SESSION_SCOPE_NOTE}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Flows Scored (session)" value={String(stats.total)} caption="Live responses, this browser" accent="red" sparkColor="var(--brand)" spark={stats.spark} icon={<Activity size={18} />} />
        <KpiCard label="Anomalies Flagged (session)" value={String(stats.anomalies)} caption="score ≥ threshold" accent="red" sparkColor="var(--brand)" spark={stats.spark} icon={<AlertTriangle size={18} />} />
        <KpiCard label="High / Critical (session)" value={String(stats.highCritical)} caption="placeholder severity bands" accent="red" sparkColor="var(--brand)" icon={<ShieldAlert size={18} />} />
        <KpiCard label="Active Threshold (live)" value={health?.active_threshold != null ? health.active_threshold.toFixed(4) : "…"} caption={health ? `${health.experiment_id} / ${health.active_operating_point}` : "loading model metadata"} accent="green" sparkColor="var(--green)" icon={<Gauge size={18} />} />
      </div>
      {stats.total === 0 && (
        <EmptyState title="No flows scored yet this session" body="Run a network flow through the live detection pipeline to populate these metrics with real backend responses. No persisted detection history exists on the server." action={runLiveCta} />
      )}
      <div className="grid gap-4 xl:grid-cols-[2fr_1.4fr_1.4fr]">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between">
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Session Scores</h2>
            <span className="rounded-full border px-3 py-1 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>Run order · this session</span>
          </div>
          {trend.length > 0 ? (
            <TrendChart data={trend} yMax={1} />
          ) : (
            <div className="mt-4"><EmptyState title="No session data" body="Anomaly scores from live runs will appear here in run order." /></div>
          )}
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="font-bold" style={{ color: "var(--text)" }}>Severity Distribution</h2>
          {stats.total > 0 ? (
            <>
              <DonutChart data={donut} centerLabel="Session flows" centerValue={String(stats.total)} />
              <div className="mt-2 space-y-1.5">
                {donut.map((d) => (
                  <div key={d.label} className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                    <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: d.color }} />{d.label}</span>
                    <span className="font-mono">{d.pct}%</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="mt-4"><EmptyState title="No session data" body="Severity bands from live runs will appear here." /></div>
          )}
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="font-bold" style={{ color: "var(--text)" }}>Attack Type Distribution</h2>
          <div className="mt-4">
            <EmptyState
              title="Not available"
              body="The backend reports statistical anomalies with retrieved ATT&CK candidates — it never attributes a definitive attack type, and no persisted history exists to aggregate. See the MITRE page for live retrieval."
            />
          </div>
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-[2.4fr_1fr]">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between">
            <h2 className="font-bold" style={{ color: "var(--text)" }}>Recent Detections</h2>
            <div className="flex items-center gap-3">
              {session.length > 0 && (
                <button onClick={clearSessionDetections} className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                  Clear session
                </button>
              )}
              <Link href="/reports" className="text-sm font-semibold" style={{ color: "var(--brand)" }}>New analysis →</Link>
            </div>
          </div>
          <div className="mt-4">
            {session.length > 0 ? (
              <SessionDetectionsTable rows={session.slice(0, 4)} />
            ) : (
              <EmptyState title="No persisted detection history is available" body="The backend is stateless and keeps no detection log. Responses you score in this browser are listed here for the session." action={runLiveCta} />
            )}
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="font-bold" style={{ color: "var(--text)" }}>System Status</h2>
          <div className="mt-4 space-y-3 text-sm">
            {[
              { label: "ML Model", value: health ? (health.model_status === "ready" ? "Running" : "Not Ready") : error ? "Unreachable" : "…", ok: health?.model_status === "ready" },
              { label: "RAG Index", value: health ? (health.rag_status === "ready" ? "Ready" : "Unavailable") : error ? "Unreachable" : "…", ok: health?.rag_status === "ready" },
              { label: "API Services", value: health ? "Healthy" : error ? "Down" : "…", ok: !!health },
              { label: "Experiment", value: health?.experiment_id ?? "…", ok: health ? true : undefined },
              { label: "Operating Point", value: health?.active_operating_point ?? "…", ok: health ? true : undefined },
              { label: "Threshold", value: health?.active_threshold != null ? health.active_threshold.toFixed(6) : "…", ok: health ? true : undefined },
            ].map((r) => (
              <div key={r.label} className="flex items-center justify-between">
                <span className="flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: r.ok == null ? "var(--text-subtle)" : r.ok ? "var(--green)" : "var(--brand)" }} />
                  {r.label}
                </span>
                <StatusPill label={r.value} tone={r.ok == null ? "neutral" : "green"} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
