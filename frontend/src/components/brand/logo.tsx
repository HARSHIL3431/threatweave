export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden>
        <circle cx="12" cy="12" r="3" fill="var(--brand)" />
        <circle cx="4" cy="6" r="2" fill="var(--text)" />
        <circle cx="20" cy="6" r="2" fill="var(--text)" />
        <circle cx="4" cy="18" r="2" fill="var(--brand)" />
        <circle cx="20" cy="18" r="2" fill="var(--text)" />
        <path d="M6 7.5L9.5 10.5M18 7.5L14.5 10.5M6 16.5L9.5 13.5M18 16.5L14.5 13.5" stroke="var(--brand)" strokeWidth="1.4" />
      </svg>
      <span className="font-extrabold tracking-wide text-sm">
        <span style={{ color: "var(--text)" }}>THREAT</span>
        <span style={{ color: "var(--brand)" }}>WEAVE</span>
      </span>
    </span>
  );
}
