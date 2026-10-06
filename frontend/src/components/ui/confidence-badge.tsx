export function ConfidenceBadge({ level }: { level: "High" | "Medium" | "Low" }) {
  const color = level === "High" ? "var(--brand)" : level === "Medium" ? "var(--amber)" : "var(--green)";
  return (
    <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color }}>
      {level} Confidence
    </span>
  );
}
