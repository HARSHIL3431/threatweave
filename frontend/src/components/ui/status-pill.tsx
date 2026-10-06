export function StatusPill({ label, tone = "green" }: { label: string; tone?: "green" | "neutral" }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
      style={{ background: tone === "green" ? "color-mix(in srgb, var(--green) 14%, transparent)" : "color-mix(in srgb, var(--text-subtle) 14%, transparent)", color: tone === "green" ? "var(--green)" : "var(--text-muted)" }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: "currentColor" }} />
      {label}
    </span>
  );
}
