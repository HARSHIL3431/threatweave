"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import {
  detectFlow,
  downloadReport,
  explainFlow,
  friendlyError,
  generateReport,
  type DetectionResponse,
  type ExplainResponse,
  type ReportResponse,
} from "@/lib/api/backend";
import { LIVE_ANOMALOUS_FLOW, LIVE_BENIGN_FLOW } from "@/lib/data/liveSamples";
import { appendSessionDetection } from "@/lib/session-store";

type Stage = "idle" | "detecting" | "explaining" | "reporting" | "downloading";

function LiveBadge() {
  return (
    <span
      className="rounded px-1.5 py-0.5 text-[10px] font-bold"
      style={{ background: "var(--green)", color: "#fff" }}
    >
      LIVE
    </span>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <h3 className="font-bold" style={{ color: "var(--text)" }}>{title}</h3>
      <div className="mt-3 space-y-2 text-sm" style={{ color: "var(--text-muted)" }}>{children}</div>
    </div>
  );
}

function Err({ e }: { e: unknown }) {
  const code = e instanceof ApiError ? e.code : "ERROR";
  return (
    <div
      className="rounded-xl border p-3 text-xs"
      style={{ borderColor: "var(--brand)", background: "var(--brand-soft)", color: "var(--text)" }}
    >
      <span className="font-mono font-bold">{code}</span>
      <span> — {friendlyError(e)}</span>
    </div>
  );
}

const btnPrimary: React.CSSProperties = {
  backgroundImage: "linear-gradient(to bottom, var(--brand-grad-from), var(--brand-grad-to))",
  color: "#fff",
};
const btnGhost: React.CSSProperties = { borderColor: "var(--border)", color: "var(--text)" };

export function LiveWorkflow() {
  const [flowText, setFlowText] = useState(() => JSON.stringify(LIVE_BENIGN_FLOW, null, 2));
  const [stage, setStage] = useState<Stage>("idle");
  const [detect, setDetect] = useState<DetectionResponse | null>(null);
  const [explain, setExplain] = useState<ExplainResponse | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const busy = stage !== "idle";

  function parseFlow(): Record<string, number> {
    const v = JSON.parse(flowText) as unknown;
    if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error("Flow must be a JSON object of feature numbers.");
    return v as Record<string, number>;
  }

  async function run(fn: () => Promise<void>, s: Stage) {
    setStage(s);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e);
    } finally {
      setStage("idle");
    }
  }

  const onDetect = () =>
    run(async () => {
      const res = await detectFlow(parseFlow());
      setDetect(res);
      appendSessionDetection(res);
      setExplain(null);
      setReport(null);
    }, "detecting");

  const onExplain = () =>
    run(async () => {
      const res = await explainFlow(parseFlow());
      setExplain(res);
      setReport(null);
    }, "explaining");

  const onReport = () =>
    run(async () => {
      const res = await generateReport(parseFlow(), 5, explain ? explain.explanation : null);
      setReport(res);
    }, "reporting");

  const onDownload = () =>
    run(async () => {
      if (!report) return;
      await downloadReport(report.report_id, report.file_name);
    }, "downloading");

  return (
    <div className="space-y-4">
      <Card title="1 · Network flow (LIVE backend input)">
        <p className="text-xs">
          Paste a full 59-feature CICIDS2017 flow (<span className="font-mono">Is_Zero_Duration</span> is computed
          server-side) or load a verified sample, then run it against the frozen E2 model.
        </p>
        <div className="flex flex-wrap gap-2">
          <button disabled={busy} onClick={() => setFlowText(JSON.stringify(LIVE_BENIGN_FLOW, null, 2))}
            className="rounded-[10px] border px-3 py-1.5 text-xs font-semibold" style={btnGhost}>Load benign sample</button>
          <button disabled={busy} onClick={() => setFlowText(JSON.stringify(LIVE_ANOMALOUS_FLOW, null, 2))}
            className="rounded-[10px] border px-3 py-1.5 text-xs font-semibold" style={btnGhost}>Load anomalous sample</button>
          <button disabled={busy} onClick={onDetect}
            className="rounded-[10px] px-4 py-1.5 text-xs font-semibold" style={btnPrimary}>
            {stage === "detecting" ? "Scoring…" : "Run live detection"}
          </button>
        </div>
        <textarea value={flowText} onChange={(e) => setFlowText(e.target.value)} rows={8} spellCheck={false}
          className="w-full rounded-xl border p-3 font-mono text-[11px]"
          style={{ background: "#0A1120", borderColor: "var(--border)", color: "#C7D2E4" }} />
      </Card>

      {error ? <Err e={error} /> : null}

      {detect && (
        <Card title="2 · Detection result">
          <p><LiveBadge /> <span className="font-mono text-xs">request {detect.request_id}</span></p>
          <p>
            Anomaly score <strong className="font-mono" style={{ color: "var(--text)" }}>{detect.detection.anomaly_score.toFixed(6)}</strong>
            {" "}vs threshold <span className="font-mono">{detect.detection.threshold.toFixed(6)}</span>
            {" "}({detect.detection.experiment_id} / {detect.detection.operating_point}) →{" "}
            <strong style={{ color: "var(--text)" }}>{detect.detection.is_anomaly ? "ANOMALOUS" : "BENIGN"}</strong>
            {" "}· severity <strong style={{ color: "var(--text)" }}>{detect.severity.level}</strong>
          </p>
          <p className="text-xs">Calibration: {detect.severity.calibration_note} — a statistical anomaly is a candidate for review, not proof of malicious activity.</p>
          <p className="text-xs">
            MITRE techniques: {detect.attack_context.mitre_techniques.length > 0
              ? (detect.attack_context.mitre_techniques as string[]).join(", ")
              : "none retrieved (RAG disabled or no candidates)"}
          </p>
          {(detect.attack_context.retrieved_context as string[]).length > 0 ? (
            <ul className="list-disc pl-5 text-xs">
              {(detect.attack_context.retrieved_context as string[]).map((c) => <li key={c} className="font-mono">{c}</li>)}
            </ul>
          ) : (
            <p className="text-xs">Retrieved context: none (does not affect the detection above).</p>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <button disabled={busy} onClick={onExplain}
              className="rounded-[10px] px-4 py-1.5 text-xs font-semibold" style={btnPrimary}>
              {stage === "explaining" ? "Explaining…" : "Get grounded AI explanation"}
            </button>
            <button disabled={busy} onClick={onReport}
              className="rounded-[10px] border px-4 py-1.5 text-xs font-semibold" style={btnGhost}>
              {stage === "reporting" ? "Generating…" : "Generate backend PDF report"}
            </button>
          </div>
        </Card>
      )}

      {explain && (
        <Card title="3 · Grounded explanation">
          <p><LiveBadge /> <span className="text-xs">provider {explain.llm.provider} · model {explain.llm.model} · {explain.llm.latency_ms} ms · schema-validated</span></p>
          <p><strong style={{ color: "var(--text)" }}>Summary.</strong> {explain.explanation.summary}</p>
          <p><strong style={{ color: "var(--text)" }}>Assessment.</strong> {explain.explanation.anomaly_assessment}</p>
          {explain.explanation.observed_indicators.length > 0 && (
            <ul className="list-disc pl-5 text-xs">
              {explain.explanation.observed_indicators.map((i) => <li key={i}>{i}</li>)}
            </ul>
          )}
          {explain.explanation.potential_attack_context.length > 0 ? (
            <ul className="list-disc pl-5 text-xs">
              {explain.explanation.potential_attack_context.map((c) => (
                <li key={c.technique_id}>
                  <span className="font-mono">{c.technique_id}</span> {c.technique_name} ({c.confidence}) — {c.reason}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs">No ATT&amp;CK candidates asserted (no retrieved context).</p>
          )}
          <p className="text-xs">Retrieved techniques are candidates only — not confirmed attacks or attribution.</p>
        </Card>
      )}

      {report && (
        <Card title="4 · Backend incident PDF">
          <p><LiveBadge /> <span className="font-mono text-xs">report {report.report_id}</span>
            {" "}<span className="text-xs">({(report.size_bytes / 1024).toFixed(1)} KB)</span></p>
          <button disabled={busy} onClick={onDownload}
            className="rounded-[10px] px-4 py-1.5 text-xs font-semibold" style={btnPrimary}>
            {stage === "downloading" ? "Downloading…" : `Download ${report.file_name}`}
          </button>
        </Card>
      )}
    </div>
  );
}
