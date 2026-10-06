"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function CodeBlock({ code, className = "" }: { code: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className={`relative rounded-xl border ${className}`} style={{ background: "#0A1120", borderColor: "var(--border)" }}>
      <button
        aria-label="Copy code"
        onClick={() => {
          navigator.clipboard.writeText(code);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
        className="absolute right-3 top-3 text-[var(--text-subtle)] hover:text-white"
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
      <pre className="overflow-x-auto p-4 font-mono text-[12.5px] leading-relaxed" style={{ color: "#C7D2E4" }}>
        <code>{code}</code>
      </pre>
    </div>
  );
}
