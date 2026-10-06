"use client";

import { Bell, ChevronDown, Search, Calendar } from "lucide-react";
import { ThemeToggle } from "@/components/brand/theme-toggle";
import { StatusPill } from "@/components/ui/status-pill";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

export function Topbar() {
  const path = usePathname();
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        document.getElementById("global-search")?.focus();
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-3" style={{ borderColor: "var(--border)" }}>
      <label className="flex w-full max-w-md items-center gap-2 rounded-[10px] border px-3 py-2" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
        <Search size={15} style={{ color: "var(--text-subtle)" }} />
        <input
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "k") (e.target as HTMLInputElement).focus();
          }}
          placeholder="Search detections, IPs, techniques..."
          className="w-full bg-transparent text-sm outline-none"
          style={{ color: "var(--text)" }}
          id="global-search"
          aria-label="Search"
        />
        <span className="rounded border px-1.5 py-0.5 font-mono text-[10px]" style={{ borderColor: "var(--border)", color: "var(--text-subtle)" }}>Ctrl K</span>
      </label>
      <div className="flex items-center gap-4">
        {path === "/analytics" && (
          <>
            <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              <Calendar size={13} /> Sep 14, 2026 - Sep 20, 2026
            </span>
            <span className="rounded-full border px-3 py-1 text-xs font-semibold" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>Last 7 days</span>
          </>
        )}
        <StatusPill label="Detection Active" />
        <ThemeToggle />
        <button aria-label="Notifications" className="relative" style={{ color: "var(--text-muted)" }}>
          <Bell size={17} />
        </button>
        <div className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-full text-sm font-bold text-white" style={{ background: "var(--brand)" }}>H</span>
          <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>Harshil</span>
          <ChevronDown size={14} style={{ color: "var(--text-subtle)" }} />
        </div>
      </div>
    </div>
  );
}
