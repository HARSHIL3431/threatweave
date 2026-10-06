"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Radar, LineChart, Shield, FileText, Database, Settings } from "lucide-react";
import { Logo } from "@/components/brand/logo";

const items = [
  { href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={17} /> },
  { href: "/detections/d1", label: "Detection", icon: <Radar size={17} /> },
  { href: "/analytics", label: "Analytics", icon: <LineChart size={17} /> },
  { href: "/mitre", label: "MITRE ATT&CK", icon: <Shield size={17} /> },
  { href: "/reports", label: "Reports", icon: <FileText size={17} /> },
  { href: "/explorer", label: "Data Explorer", icon: <Database size={17} /> },
  { href: "/settings", label: "Settings", icon: <Settings size={17} /> },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="hidden w-[220px] shrink-0 flex-col border-r p-4 md:flex" style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}>
      <Link href="/" className="px-2 py-3"><Logo /></Link>
      <nav className="mt-6 flex flex-col gap-1">
        {items.map((it) => {
          const active = it.href === "/detections/d1" ? path.startsWith("/detections") : path === it.href;
          return (
            <Link key={it.href} href={it.href}
              className={active
                ? "flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-sm font-semibold transition-colors bg-[var(--brand-soft)] text-[var(--brand)] dark:text-white dark:bg-[image:linear-gradient(to_right,var(--brand-grad-from),var(--brand-grad-to))] dark:shadow-[var(--active-glow)]"
                : "flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-sm font-semibold transition-colors text-[var(--text-muted)]"}>
              {it.icon}{it.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
