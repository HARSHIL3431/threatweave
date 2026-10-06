import Link from "next/link";
import type { Detection } from "@/lib/types";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { TechniqueChip } from "@/components/ui/technique-chip";

const typeColor: Record<string, string> = {
  "Port Scan": "var(--brand)",
  DDoS: "var(--brand)",
  "Web Attack": "var(--amber)",
  Infiltration: "var(--brand)",
  "Brute Force": "var(--brand)",
  Other: "var(--text-muted)",
};

export function DetectionsTable({ rows }: { rows: Detection[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[13px]">
        <thead>
          <tr className="text-xs" style={{ color: "var(--text-subtle)" }}>
            {["Time", "Type", "Source IP", "Destination IP", "Score", "Severity", "MITRE Technique", "Action"].map((h) => (
              <th key={h} className="pb-3 pr-4 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <tr key={d.id} className="border-t" style={{ borderColor: "var(--border)" }}>
              <td className="py-3 pr-4 font-mono" style={{ color: "var(--text-muted)" }}>{d.timestamp.slice(11, 19)}</td>
              <td className="py-3 pr-4 font-semibold" style={{ color: typeColor[d.type] }}>{d.type}</td>
              <td className="py-3 pr-4 font-mono" style={{ color: "var(--text)" }}>{d.srcIp}</td>
              <td className="py-3 pr-4 font-mono" style={{ color: "var(--text)" }}>{d.dstIp}</td>
              <td className="py-3 pr-4 font-mono" style={{ color: "var(--text)" }}>{d.score.toFixed(2)}</td>
              <td className="py-3 pr-4"><SeverityBadge severity={d.severity} /></td>
              <td className="py-3 pr-4"><TechniqueChip id={d.technique} /></td>
              <td className="py-3 pr-4">
                <Link href={`/detections/${d.id}`} className="rounded-[8px] border px-3 py-1 text-xs font-semibold" style={{ borderColor: "var(--border)", color: "var(--text)" }}>View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
