export function TwoToneHeading({ lead, accent, className = "" }: { lead: string; accent: string; className?: string }) {
  return (
    <h2 className={`font-extrabold tracking-[-0.02em] leading-[1.05] ${className}`}>
      <span style={{ color: "var(--text)" }}>{lead} </span>
      <span style={{ color: "var(--brand)" }}>{accent}</span>
    </h2>
  );
}
