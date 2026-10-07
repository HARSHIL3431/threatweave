import { AlertTriangle } from "lucide-react";

interface PipelineErrorCardProps {
  stage: string;
  message: string;
  status?: string;
  onRetry?: () => void;
}

export function PipelineErrorCard({ stage, message, status = "Failed", onRetry }: PipelineErrorCardProps) {
  return (
    <div className="relative mx-auto w-full max-w-xl pt-3">
      <div aria-hidden className="absolute inset-x-6 top-0 h-full translate-y-2 rounded-2xl border" style={{ background: "var(--surface)", borderColor: "var(--border)", opacity: 0.35 }} />
      <div aria-hidden className="absolute inset-x-3 top-0 h-full translate-y-1 rounded-2xl border" style={{ background: "var(--surface)", borderColor: "var(--border)", opacity: 0.55 }} />
      <div role="alert" className="relative rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--brand)", boxShadow: "0 0 0 1px var(--brand), 0 0 20px color-mix(in srgb, var(--brand) 25%, transparent)" }}>
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} style={{ color: "var(--brand)" }} />
          <span className="text-sm font-bold" style={{ color: "var(--text)" }}>Pipeline Error</span>
          <span className="ml-auto rounded-full border px-2.5 py-0.5 text-[11px] font-semibold" style={{ borderColor: "var(--brand)", color: "var(--brand)", background: "var(--brand-soft)" }}>{status}</span>
        </div>
        <div className="mt-3 text-[12px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Affected stage</div>
        <div className="mt-0.5 text-sm font-bold" style={{ color: "var(--text)" }}>{stage}</div>
        <div className="mt-3 rounded-xl border p-3 font-mono text-[12.5px] leading-relaxed" style={{ background: "#0A1120", borderColor: "var(--border)", color: "#C7D2E4" }}>{message}</div>
        {onRetry && (
          <button onClick={onRetry} className="mt-4 rounded-[10px] border px-4 py-2 text-sm font-semibold" style={{ borderColor: "var(--brand)", color: "var(--brand)" }}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
