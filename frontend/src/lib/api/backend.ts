import { apiBase, apiFetch, ApiError } from "./client";

export type HealthResponse = {
  status: string;
  model_status: string;
  model_version: string | null;
  experiment_id: string | null;
  active_operating_point: string | null;
  active_threshold: number | null;
  rag_status?: string;
  timestamp: string;
};

export type DetectionResponse = {
  request_id: string;
  detection: {
    is_anomaly: boolean;
    anomaly_score: number;
    threshold: number;
    experiment_id: string;
    operating_point: string;
  };
  severity: { level: string; risk_score: number; calibration_note: string };
  attack_context: { mitre_techniques: unknown[]; retrieved_context: unknown[] };
  explanation: { summary: string | null; reasoning: string | null; recommendations: string[] };
  metadata: { model_version: string; source_dataset: string; timestamp: string };
};

export type BatchResponse = {
  batch_id: string;
  count: number;
  results: DetectionResponse[];
  timestamp: string;
};

export type RagStatusResponse = {
  status: string;
  index_path?: string | null;
  embedding_model?: string | null;
  embedding_dim?: number | null;
  doc_count?: number | null;
  technique_count?: number | null;
  subtechnique_count?: number | null;
  detail?: string | null;
  timestamp: string;
};

export type RagSearchResult = {
  technique_id: string;
  technique_name: string;
  score: number;
  description: string;
  tactics: string[];
  detection: string | null;
  mitigations: string[];
  technique_type: string;
};

export type RagQueryResponse = {
  query: string;
  top_k: number;
  result_count: number;
  retrieval_time_ms: number;
  results: RagSearchResult[];
};

export type ExplainAttackContext = {
  technique_id: string;
  technique_name: string;
  confidence: string;
  reason: string;
};

export type ExplainResponse = {
  request_id: string;
  detection: DetectionResponse["detection"];
  severity: DetectionResponse["severity"];
  attack_context: { mitre_techniques: string[]; retrieved_context: string[] };
  explanation: {
    summary: string;
    anomaly_assessment: string;
    observed_indicators: string[];
    potential_attack_context: ExplainAttackContext[];
    recommended_actions: string[];
    limitations: string[];
  };
  llm: { provider: string; model: string; latency_ms: number; validated: boolean };
};

export type ReportResponse = {
  report_id: string;
  request_id: string;
  report_type: string;
  app_name: string;
  status: string;
  file_name: string;
  pdf_path: string;
  download_url: string;
  size_bytes: number;
  generated_at: string;
};

export function friendlyError(e: unknown): string {
  if (e instanceof ApiError) {
    switch (e.code) {
      case "NETWORK_ERROR":
        return "Backend unreachable. Start the backend (uvicorn app.main:app --port 8001) and retry.";
      case "TIMEOUT":
        return "Backend request timed out. The model or RAG index may still be loading; retry shortly.";
      case "LLM_UNAVAILABLE":
        return "AI explanation unavailable (LLM disabled or no API key). Detection results above are unaffected.";
      case "RAG_UNAVAILABLE":
        return "MITRE ATT&CK knowledge base unavailable (index not built or RAG disabled). Detection results above are unaffected.";
      case "MODEL_NOT_READY":
        return "ML model not ready. Check backend health and artifact paths, then retry.";
      case "INVALID_INPUT":
        return `Invalid flow input: ${e.message}`;
      case "MOCK_MODE":
        return e.message;
      default:
        return `${e.code}: ${e.message}`;
    }
  }
  return e instanceof Error ? e.message : "Unknown error";
}

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true" || process.env.USE_MOCK === "true";

const mockHealth: HealthResponse = {
  status: "healthy",
  model_status: "ready",
  model_version: "isolation_forest_v1",
  experiment_id: "with_port",
  active_operating_point: "OP-A",
  active_threshold: 0.521919,
  rag_status: "ready",
  timestamp: "2026-09-20T14:23:06Z",
};

export const getHealth = () => (USE_MOCK ? Promise.resolve(mockHealth) : apiFetch<HealthResponse>("/v1/health"));
export const detectFlow = (flow: Record<string, number>) =>
  USE_MOCK
    ? Promise.resolve<DetectionResponse>({
        request_id: "mock", detection: { is_anomaly: false, anomaly_score: 0.45, threshold: 0.521919, experiment_id: "with_port", operating_point: "OP-A" },
        severity: { level: "info", risk_score: 0.45, calibration_note: "INITIAL PLACEHOLDER CALIBRATION" },
        attack_context: { mitre_techniques: [], retrieved_context: [] },
        explanation: { summary: null, reasoning: null, recommendations: [] },
        metadata: { model_version: "isolation_forest_v1", source_dataset: "CICIDS2017", timestamp: mockHealth.timestamp },
      })
    : apiFetch<DetectionResponse>("/v1/detect", { method: "POST", body: JSON.stringify(flow) });
export const detectBatch = (flows: Record<string, number>[]) =>
  apiFetch<BatchResponse>("/v1/detect/batch", { method: "POST", body: JSON.stringify({ flows }) });

function mockGuard(name: string): void {
  if (USE_MOCK) throw new ApiError("MOCK_MODE", `${name} needs the live backend. Set NEXT_PUBLIC_USE_MOCK=false and start the backend.`);
}

export const getRagStatus = () => {
  mockGuard("MITRE ATT&CK search");
  return apiFetch<RagStatusResponse>("/v1/rag/status");
};

export const queryRag = (query: string, top_k = 5) => {
  mockGuard("MITRE ATT&CK search");
  return apiFetch<RagQueryResponse>("/v1/rag/query", { method: "POST", body: JSON.stringify({ query, top_k }) });
};

export const explainFlow = (flow: Record<string, number>, top_k = 5) => {
  mockGuard("AI explanation");
  return apiFetch<ExplainResponse>("/v1/explain", { method: "POST", body: JSON.stringify({ flow, top_k }) }, 90000);
};

export const generateReport = (
  flow: Record<string, number>,
  top_k = 5,
  llm_explanation: ExplainResponse["explanation"] | null = null
) => {
  mockGuard("Backend report generation");
  return apiFetch<ReportResponse>(
    "/v1/reports/generate",
    { method: "POST", body: JSON.stringify({ report_type: "analysis", flow, top_k, llm_explanation }) },
    90000
  );
};

const REPORT_ID_RE = /^[0-9a-f]{32}$/;

export async function downloadReport(report_id: string, file_name: string): Promise<void> {
  mockGuard("Backend report download");
  if (!REPORT_ID_RE.test(report_id)) throw new ApiError("INVALID_REPORT_ID", "Invalid report identifier.");
  const res = await fetch(`${apiBase()}/v1/reports/${report_id}/download`);
  if (!res.ok) throw new ApiError(`HTTP_${res.status}`, `Report download failed with status ${res.status}.`, res.status);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = file_name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
