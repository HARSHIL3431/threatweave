import Link from "next/link";
import type { DetectionResponse } from "@/lib/api/backend";
import { SeverityBadge } from "@/components/ui/severity-badge";
import type { Severity } from "@/lib/types";

const toSeverity = (level: string): Severity => {
  const u = level.toUpperCase();
  return u === "CRITICAL" || u === "HIGH" || u === "MEDIUM" || u === "LOW" ? (u as Severity) : "INFO";
};

const timeOf = (r: DetectionResponse) => (r.metadata.timestamp ?? "").slice(11, 19) || "—";

/** Table of REAL backend responses recorded in this browser session. */
export function SessionDetectionsTable({ rows }: { rows: DetectionResponse[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[13px]">
        <thead>
          <tr className="text-xs" style={{ color: "var(--text-subtle)" }}>
            {["Time", "Score", "Threshold", "Verdict", "Severity", "Request", "Action"].map((h) => (
              <th key={h} className="pb-3 pr-4 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.request_id} className="border-t" style={{ borderColor: "var(--border)" }}>
              <td className="py-3 pr-4 font-mono" style={{ color: "var(--text-muted)" }}>{timeOf(r)}</td>
              <td className="py-3 pr-4 font-mono" style={{ color: "var(--text)" }}>{r.detection.anomaly_score.toFixed(4)}</td>
              <td className="py-3 pr-4 font-mono" style={{ color: "var(--text-muted)" }}>{r.detection.threshold.toFixed(4)}</td>
              <td className="py-3 pr-4 font-semibold" style={{ color: r.detection.is_anomaly ? "var(--brand)" : "var(--text-muted)" }}>
                {r.detection.is_anomaly ? "ANOMALOUS" : "BENIGN"}
              </td>
              <td className="py-3 pr-4"><SeverityBadge severity={toSeverity(r.severity.level)} /></td>
              <td className="py-3 pr-4 font-mono text-[11px]" style={{ color: "var(--text-subtle)" }}>{r.request_id.slice(0, 8)}…</td>
              <td className="py-3 pr-4">
                <Link href={`/detections/${r.request_id}`} className="rounded-[8px] border px-3 py-1 text-xs font-semibold" style={{ borderColor: "var(--border)", color: "var(--text)" }}>View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
