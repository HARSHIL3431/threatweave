export function IconTile({ children, color = "var(--brand)", size = 48 }: { children: React.ReactNode; color?: string; size?: number }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-xl"
      style={{ width: size, height: size, background: `color-mix(in srgb, ${color} 12%, transparent)`, color }}
    >
      {children}
    </span>
  );
}
