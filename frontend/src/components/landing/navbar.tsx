"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/brand/theme-toggle";
import { Button } from "@/components/ui/button";

const links = [
  { label: "Platform", href: "#platform" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Features", href: "#features" },
  { label: "Demo", href: "#demo" },
  { label: "Documentation", href: "#documentation" },
];

export function Navbar() {
  return (
    <header className="sticky top-4 z-40 mx-auto flex max-w-[1360px] items-center justify-between rounded-[20px] border px-6 py-3 backdrop-blur-md"
      style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--surface) 75%, transparent)" }}>
      <Link href="/"><Logo /></Link>
      <nav className="hidden items-center gap-7 md:flex">
        {links.map((l) => (
          <a key={l.label} href={l.href} className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
            {l.label}
          </a>
        ))}
      </nav>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <Link href="/dashboard">
          <Button>Open Dashboard <ArrowRight size={16} /></Button>
        </Link>
      </div>
    </header>
  );
}
