export function ComingSoon({ title }: { title: string }) {
  return (
    <div className="grid h-64 place-items-center rounded-2xl border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="text-center">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>{title}</h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>Coming soon</p>
      </div>
    </div>
  );
}
