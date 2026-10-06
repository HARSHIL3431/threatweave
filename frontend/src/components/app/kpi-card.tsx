import { Sparkline } from "@/components/charts/charts";
import { IconTile } from "@/components/ui/icon-tile";
import { TrendingUp } from "lucide-react";

export function KpiCard({ label, value, delta, accent, sparkColor, spark, icon }: { label: string; value: string; delta: string; accent: "red" | "green"; sparkColor: string; spark: number[]; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--card-shadow)" }}>
      <IconTile color={accent === "red" ? "var(--brand)" : "var(--green)"} size={44}>
        {icon}
      </IconTile>
      <div className="min-w-0 flex-1">
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</div>
        <div className="text-3xl font-extrabold" style={{ color: "var(--text)" }}>{value}</div>
        <div className="flex items-center gap-1 text-[11px] font-semibold" style={{ color: "var(--green)" }}>
          <TrendingUp size={11} /> {delta}
        </div>
      </div>
      <div className="w-24"><Sparkline data={spark} color={sparkColor} /></div>
    </div>
  );
}
