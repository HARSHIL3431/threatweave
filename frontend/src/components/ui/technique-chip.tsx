export function TechniqueChip({ id }: { id: string }) {
  return (
    <span className="rounded border px-1.5 py-0.5 font-mono text-[11px]" style={{ borderColor: "var(--border)", color: "var(--blue)" }}>
      {id}
    </span>
  );
}
