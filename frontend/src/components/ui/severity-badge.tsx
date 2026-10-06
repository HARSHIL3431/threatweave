import type { Severity } from "@/lib/types";

const styles: Record<Severity, { bg: string; fg: string }> = {
  CRITICAL: { bg: "var(--brand)", fg: "#fff" },
  HIGH: { bg: "color-mix(in srgb, var(--brand) 15%, transparent)", fg: "var(--brand)" },
  MEDIUM: { bg: "color-mix(in srgb, var(--amber) 18%, transparent)", fg: "var(--amber)" },
  LOW: { bg: "color-mix(in srgb, var(--green) 15%, transparent)", fg: "var(--green)" },
  INFO: { bg: "color-mix(in srgb, var(--text-subtle) 15%, transparent)", fg: "var(--text-muted)" },
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const s = styles[severity];
  return (
    <span className="rounded-md px-2 py-0.5 text-[11px] font-bold uppercase" style={{ background: s.bg, color: s.fg }}>
      {severity === "INFO" ? "INFORMATIONAL" : severity}
    </span>
  );
}
