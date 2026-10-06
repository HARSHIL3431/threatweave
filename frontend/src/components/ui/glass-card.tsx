export function GlassCard({
  children, active = false, className = "",
}: { children: React.ReactNode; active?: boolean; className?: string }) {
  return (
    <div
      className={`rounded-2xl border p-5 ${className}`}
      style={{
        background: "var(--surface)",
        borderColor: active ? "var(--brand)" : "var(--border)",
        boxShadow: active ? "var(--active-glow)" : "var(--card-shadow)",
      }}
    >
      {children}
    </div>
  );
}
