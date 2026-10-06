export function StepCard({
  n, title, description, icon, accent, active, onClick,
}: {
  n: string; title: string; description: string; icon: React.ReactNode; accent: string; active?: boolean; onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex min-w-[180px] max-w-[220px] flex-col items-start gap-2 rounded-2xl border p-4 text-left transition-all"
      style={{
        background: "var(--surface)",
        borderColor: active ? "var(--brand)" : "var(--border)",
        boxShadow: active ? "var(--active-glow)" : "var(--card-shadow)",
      }}
    >
      <span className="rounded-md px-1.5 py-0.5 font-mono text-[11px] font-bold" style={{ background: `color-mix(in srgb, ${accent} 15%, transparent)`, color: accent }}>
        {n}
      </span>
      <span style={{ color: accent }}>{icon}</span>
      <span className="text-sm font-bold" style={{ color: "var(--text)" }}>{title}</span>
      <span className="text-[12px] leading-snug" style={{ color: "var(--text-muted)" }}>{description}</span>
    </button>
  );
}
