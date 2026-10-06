import { apiFetch } from "./client";

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
