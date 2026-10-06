export function EyebrowBadge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.08em]"
      style={{ color: "var(--brand)", background: "var(--brand-soft)", borderColor: "rgba(229,19,43,0.35)" }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--brand)" }} />
      {children}
    </span>
  );
}
