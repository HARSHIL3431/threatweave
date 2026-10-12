"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { friendlyError, getRagStatus, queryRag, type RagQueryResponse, type RagStatusResponse } from "@/lib/api/backend";

export default function Mitre() {
  const [status, setStatus] = useState<RagStatusResponse | null>(null);
  const [statusErr, setStatusErr] = useState<unknown>(null);
  const [query, setQuery] = useState("port scan reconnaissance network discovery");
  const [result, setResult] = useState<RagQueryResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    getRagStatus()
      .then((s) => alive && setStatus(s))
      .catch((e) => alive && setStatusErr(e));
    return () => { alive = false; };
  }, []);

  const search = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await queryRag(query, 5));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-bold" style={{ color: "var(--text)" }}>MITRE ATT&amp;CK</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Live retrieval over the backend MITRE ATT&amp;CK knowledge base. Results are grounded candidates,
          not confirmed detections.
        </p>
      </div>

      <div className="rounded-2xl border p-5 text-sm" style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text-muted)" }}>
        {status ? (
          <div>
            <p>
              Index status: <strong style={{ color: "var(--text)" }}>{status.status}</strong>
              {status.status === "ready" && (
                <span className="text-xs"> · {status.technique_count} techniques / {status.subtechnique_count} sub-techniques · {status.embedding_model}</span>
              )}
            </p>
            {status.status === "ready" && (
              <p className="mt-1 text-xs">
                {status.knowledge_age_status === "unknown" || status.built_at == null ? (
                  <span>Knowledge age: unknown (index predates provenance tracking; build date unavailable).</span>
                ) : (
                  <span>
                    Index built {status.built_at.slice(0, 10)} ({status.knowledge_age_days} days ago)
                    {status.is_stale ? (
                      <strong style={{ color: "var(--brand)" }}> — stale (&gt;180 days old)</strong>
                    ) : (
                      <span> — fresh</span>
                    )}
                    . Build date is not the ATT&amp;CK release date
                    {status.attack_version ? ` (release ${status.attack_version})` : " (release unknown)"}.
                  </span>
                )}
              </p>
            )}
          </div>
        ) : statusErr ? (
          <p><span className="font-mono font-bold">{statusErr instanceof ApiError ? statusErr.code : "ERROR"}</span> — {friendlyError(statusErr)}</p>
        ) : (
          <p>Checking knowledge-base status…</p>
        )}
      </div>

      <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. data exfiltration over encrypted channel"
            className="flex-1 rounded-[10px] border px-3 py-2 text-sm"
            style={{ borderColor: "var(--border)", background: "transparent", color: "var(--text)" }} />
          <button disabled={busy} onClick={search}
            className="rounded-[10px] px-5 py-2 text-sm font-semibold text-white"
            style={{ backgroundImage: "linear-gradient(to bottom, var(--brand-grad-from), var(--brand-grad-to))" }}>
            {busy ? "Searching…" : "Search techniques"}
          </button>
        </div>
        {error ? (
          <p className="mt-3 rounded-xl border p-3 text-xs" style={{ borderColor: "var(--brand)", background: "var(--brand-soft)", color: "var(--text)" }}>
            <span className="font-mono font-bold">{error instanceof ApiError ? error.code : "ERROR"}</span> — {friendlyError(error)}
          </p>
        ) : null}
        {result && (
          <div className="mt-4 space-y-3">
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {result.result_count} result(s) in {result.retrieval_time_ms.toFixed(1)} ms
            </p>
            {result.results.map((r) => (
              <div key={r.technique_id} className="rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-[var(--brand-soft)] px-1.5 py-0.5 font-mono text-[11px] font-bold" style={{ color: "var(--brand)" }}>{r.technique_id}</span>
                  <span className="text-sm font-bold" style={{ color: "var(--text)" }}>{r.technique_name}</span>
                  <span className="font-mono text-[11px]" style={{ color: "var(--text-muted)" }}>score {r.score.toFixed(4)}</span>
                </div>
                {r.tactics.length > 0 && <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Tactics: {r.tactics.join(", ")}</p>}
                {r.description && <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>{r.description.slice(0, 400)}{r.description.length > 400 ? "…" : ""}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
