"use client";

import { Area, AreaChart, Cell, Pie, PieChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Line, LineChart, CartesianGrid } from "recharts";

export function Sparkline({ data, color = "var(--brand)" }: { data: number[]; color?: string }) {
  const d = data.map((v, i) => ({ i, v }));
  const id = `sg-${data.length}-${Math.abs(color.length)}`;
  return (
    <ResponsiveContainer width="100%" height={36}>
      <AreaChart data={d}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} fill={`url(#${id})`} strokeWidth={1.5} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({ data, centerLabel, centerValue }: { data: { label: string; pct: number; color: string }[]; centerLabel: string; centerValue: string }) {
  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie data={data} dataKey="pct" nameKey="label" innerRadius={52} outerRadius={72} paddingAngle={2} strokeWidth={0}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="text-2xl font-bold" style={{ color: "var(--text)" }}>{centerValue}</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>{centerLabel}</div>
        </div>
      </div>
    </div>
  );
}

export function BarList({ items }: { items: { label: string; pct: number; color: string }[] }) {
  return (
    <div className="flex flex-col gap-2.5">
      {items.map((it) => (
        <div key={it.label} className="flex items-center gap-3">
          <span className="w-28 shrink-0 truncate text-xs" style={{ color: "var(--text-muted)" }}>{it.label}</span>
          <div className="h-2 flex-1 rounded-full" style={{ background: "color-mix(in srgb, var(--text-subtle) 18%, transparent)" }}>
            <div className="h-2 rounded-full" style={{ width: `${it.pct}%`, background: it.color }} />
          </div>
          <span className="w-9 text-right font-mono text-xs" style={{ color: "var(--text)" }}>{it.pct}%</span>
        </div>
      ))}
    </div>
  );
}

export function TrendChart({ data, yMax }: { data: { t?: string; day?: string; v: number }[]; yMax?: number }) {
  const xKey = data[0] && "day" in data[0] ? "day" : "t";
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: "var(--text-subtle)", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis domain={[0, yMax ?? "auto"]} tick={{ fill: "var(--text-subtle)", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
        <Tooltip
          contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text)", fontSize: 12 }}
        />
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.25} />
            <stop offset="100%" stopColor="var(--brand)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Line type="monotone" dataKey="v" stroke="var(--brand)" strokeWidth={2} dot={{ r: 3, fill: "var(--brand)" }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function Gauge({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value));
  const angle = 180 * (1 - pct);
  const r = 80;
  const rad = (a: number) => (a * Math.PI) / 180;
  const x = (a: number) => 100 + r * Math.cos(rad(a));
  const y = (a: number) => 100 - r * Math.sin(rad(a));
  const largeArc = 0;
  return (
    <svg viewBox="0 0 200 118" className="w-full" role="img" aria-label={`Anomaly Score ${value.toFixed(2)} out of 1`}>
      <path d={`M ${x(180)} ${y(180)} A ${r} ${r} 0 0 1 ${x(0)} ${y(0)}`} fill="none" stroke="var(--border)" strokeWidth="12" strokeLinecap="round" />
      <path d={`M ${x(180)} ${y(180)} A ${r} ${r} 0 ${largeArc} 1 ${x(angle)} ${y(angle)}`} fill="none" stroke="var(--brand)" strokeWidth="12" strokeLinecap="round" />
      <text x="100" y="92" textAnchor="middle" fontSize="28" fontWeight="800" fill="var(--text)">{value.toFixed(2)}</text>
      <text x="100" y="108" textAnchor="middle" fontSize="9" fill="var(--text-muted)">Anomaly Score</text>
      <text x="20" y="114" fontSize="9" fill="var(--text-subtle)">0</text>
      <text x="172" y="114" fontSize="9" fill="var(--text-subtle)">1</text>
    </svg>
  );
}
