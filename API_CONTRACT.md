# Backend API Contract

**Status:** Implemented and verified 2026-10-09 (8 routes; backend suite 132 passed: 87 unit + 45 integration)

This document describes the stable FastAPI contract exposed by the backend: frozen E2 Isolation Forest
detection, MITRE ATT&CK RAG retrieval, grounded LLM explanations, and server-side PDF reports.
The backend keeps **no server-side detection-history persistence** (no database, no record-listing endpoint);
per-flow analysis is stateless. Dashboard/analytics history shown in the UI comes from the browser session store.

## Base API

- Base path: `/api/v1`
- JSON request and response bodies
- Optional request correlation header: `X-Correlation-ID`
- Interactive documentation: `/docs`
- OpenAPI document: `/openapi.json`

### Frontend proxy vs backend paths

The browser never calls the backend directly. The Next.js dev/prod server rewrites `/api/:path*` to
`http://localhost:8001/api/:path*` (see `frontend/next.config.ts`), and the frontend uses
`NEXT_PUBLIC_API_BASE_URL=/api`. The paths below are backend paths; the UI reaches them through the proxy
(e.g. UI `/api/v1/health` → backend `http://localhost:8001/api/v1/health`).

## Endpoints

| Method | Endpoint | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | None | `HealthResponse` |
| `POST` | `/api/v1/detect` | `NetworkFlowRequest` | `DetectionResponse` |
| `POST` | `/api/v1/detect/batch` | `BatchDetectionRequest` | `BatchDetectionResponse` |
| `GET` | `/api/v1/rag/status` | None | `RagStatusResponse` |
| `POST` | `/api/v1/rag/query` | `RagQueryRequest` | `RagQueryResponse` |
| `POST` | `/api/v1/explain` | `ExplainRequest` | `ExplainResponse` |
| `POST` | `/api/v1/reports/generate` | `ReportGenerateRequest` | `ReportResponse` |
| `GET` | `/api/v1/reports/{report_id}/download` | 32-hex `report_id` path param | `application/pdf` |

## Health

`GET /api/v1/health` reports application/model readiness plus the RAG index state.

```json
{
  "status": "healthy",
  "model_status": "ready",
  "model_version": "isolation_forest_v1",
  "experiment_id": "with_port",
  "active_operating_point": "OP-A",
  "active_threshold": 0.521919,
  "rag_status": "ready",
  "timestamp": "2026-10-09T16:41:01+00:00"
}
```

When artifacts are unavailable, the application reports `status: "degraded"` and `model_status: "not_loaded"`.
`rag_status` is `"ready"` when the FAISS index loads, otherwise `"unavailable"`. The index is preloaded
best-effort at startup, so `rag_status` can be `ready` even when detection-time retrieval is disabled
(see RAG section).

## Single Detection

`POST /api/v1/detect` accepts one CICIDS-style network flow. The request uses the exact feature aliases in
`backend/app/schemas/detection.py`. The frozen E2 contract contains 60 features, with `Is_Zero_Duration`
computed by the service when omitted. All values must be finite numbers and extra fields are rejected.

The authoritative feature order and transformation lists are loaded from:

```text
data/processed/experiments/with_port/preprocessing_config.json
```

They are validated against the model metadata before serving requests.

The response is:

```json
{
  "request_id": "request-123",
  "detection": {
    "is_anomaly": true,
    "anomaly_score": 0.540229,
    "threshold": 0.521919,
    "experiment_id": "with_port",
    "operating_point": "OP-A"
  },
  "severity": {
    "level": "medium",
    "risk_score": 0.540229,
    "calibration_note": "INITIAL PLACEHOLDER CALIBRATION"
  },
  "attack_context": {
    "mitre_techniques": [],
    "retrieved_context": ["[retrieved-not-confirmed] T1011 Exfiltration Over Other Network Medium (exfiltration) score=0.4559"]
  },
  "explanation": {
    "summary": null,
    "reasoning": null,
    "recommendations": []
  },
  "metadata": {
    "model_version": "isolation_forest_v1",
    "source_dataset": "CICIDS2017",
    "timestamp": "2026-10-09T16:41:01+00:00"
  }
}
```

`anomaly_score` is computed as `-model.score_samples()`, so higher values are more anomalous. `is_anomaly` is
true when the score is greater than or equal to the active frozen threshold.

- `attack_context.mitre_techniques` is populated only when `MITRE_ENABLED=true` (default `false`).
- `attack_context.retrieved_context` is populated only when `RAG_ENABLED=true` (default `false`); entries are
  always labeled `retrieved-not-confirmed` and are candidates, never confirmed detections.
- The `/detect` explanation hook is intentionally a no-op (`summary`/`reasoning` null): the LLM is only
  invoked through `/explain`, so detection never depends on an LLM provider.
- The current response does not include a standalone `detected_features` attribution field because no
  per-feature explanation layer exists.

## Batch Detection

`POST /api/v1/detect/batch` accepts `{ "flows": [...] }` where each flow satisfies the complete
`NetworkFlowRequest` contract. Results preserve input order. An empty `flows` list returns HTTP 200 with
`count: 0` and `results: []`. Any invalid flow fails request validation; values are never silently imputed.

## RAG Status and Query

`GET /api/v1/rag/status` returns the index state without rebuilding anything:

```json
{
  "status": "ready",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_dim": 384,
  "doc_count": 697,
  "technique_count": 222,
  "subtechnique_count": 475
}
```

`POST /api/v1/rag/query` accepts `{ "query": "<1–2000 chars>", "top_k": 5 }` (`top_k` 1–50) and returns grounded
MITRE ATT&CK techniques with cosine-similarity scores, tactics, descriptions, detections, and mitigations.
A blank query returns 422. When the index is missing, the endpoint returns `503 RAG_UNAVAILABLE`
(run `scripts/build_mitre_index.py`); ML detection keeps working regardless.

## Explanation

`POST /api/v1/explain` accepts `{ "flow": <NetworkFlowRequest>, "top_k": 5 }` (`top_k` 1–20). It re-runs the
standard pipeline (ML → severity → RAG retrieval) on the supplied flow, then asks the configured provider for
a strictly validated structured explanation:

```json
{
  "request_id": "request-123",
  "detection": {},
  "severity": {},
  "attack_context": {},
  "explanation": {
    "summary": "...",
    "anomaly_assessment": "...",
    "observed_indicators": ["..."],
    "potential_attack_context": [
      { "technique_id": "T1011", "technique_name": "...", "confidence": "medium", "reason": "..." }
    ],
    "recommended_actions": ["..."],
    "limitations": ["..."]
  },
  "llm": { "provider": "mock", "model": "mock-grounded-local", "latency_ms": 0.07, "validated": true }
}
```

Grounding enforcement: every `technique_id` in the output must be one of the IDs RAG just retrieved, each
name must match the RAG name, and confidence is one of `low`/`medium`/`high`. Violations return
`502 LLM_VALIDATION_ERROR` — output is never silently accepted.

- `LLM_ENABLED=false` (default) or a missing API key returns `503 LLM_UNAVAILABLE`. Detection is unaffected.
- `LLM_PROVIDER=mock` (deterministic, offline, no key or cost) derives the explanation only from the supplied
  evidence; mock success validates plumbing and grounding, **not** real-LLM quality.

## Reports

`POST /api/v1/reports/generate` accepts
`{ "report_type": "analysis"|"anomaly"|"benign", "app_name": "...", "request_id": null, "flow": <NetworkFlowRequest>, "top_k": 5, "llm_explanation": null }`.
It re-runs the shared analysis pipeline (ML → severity → RAG) and renders a server-side PDF containing the
detection summary, observed indicators, retrieved MITRE context (candidates only), and — when supplied — an
LLM explanation that is **re-validated** against the freshly retrieved technique IDs before rendering.

The response carries a server-generated 32-hex `report_id`:

```json
{
  "report_id": "4c967822ec134efb97d34fd89eb7a5d4",
  "request_id": "request-123",
  "file_name": "report_4c967822ec134efb97d34fd89eb7a5d4.pdf",
  "download_url": "/api/v1/reports/4c967822ec134efb97d34fd89eb7a5d4/download",
  "size_bytes": 5330
}
```

`GET /api/v1/reports/{report_id}/download` streams the PDF (`Content-Type: application/pdf`, `%PDF-`
signature). Filenames are server-generated UUIDs; user input never becomes a path. Malformed or unknown IDs
return controlled `404 REPORT_NOT_FOUND` — path traversal is impossible.

## Error Contract

All application errors use `ErrorResponse` (`error_code`, `message`, `details`, `timestamp`, `request_id`):

| Error code | HTTP status | Meaning |
| --- | ---: | --- |
| `INVALID_INPUT` | 422 | Invalid request data: missing, non-numeric, NaN, Infinity, blank query, or extra fields |
| `FEATURE_MISMATCH` | 422 | Feature contract or preprocessing configuration mismatch |
| `MODEL_NOT_READY` | 503 | Model or preprocessing artifact is unavailable or invalid |
| `INFERENCE_ERROR` | 500 | Preprocessing or model scoring failed (details logged server-side only) |
| `INTERNAL_ERROR` | 500 | Unexpected server failure |
| `RAG_UNAVAILABLE` | 503 | RAG index missing or disabled for the standalone query surface |
| `LLM_UNAVAILABLE` | 503 | LLM disabled (`LLM_ENABLED=false`), unknown provider, or no API key |
| `LLM_PROVIDER_ERROR` | 502 | Provider transport/HTTP error |
| `LLM_TIMEOUT` | 504 | Provider call exceeded `LLM_TIMEOUT` |
| `LLM_VALIDATION_ERROR` | 502 | LLM output failed schema/grounding validation |
| `REPORT_ERROR` | 500 | PDF rendering or file-write failure |
| `REPORT_NOT_FOUND` | 404 | Invalid or unknown report identifier |

## Frozen Policy

```text
Experiment: with_port
Feature count: 60
Model version: isolation_forest_v1
Default operating point: OP-A
OP-A threshold: 0.5219193851693676
OP-B threshold: 0.4878500998020172
```

`ACTIVE_OPERATING_POINT` selects `OP-A` or `OP-B`; the API provides no runtime threshold tuning or mutation endpoint.

## Verification

Verified 2026-10-09 over live HTTP:

- Health, single detection (benign 0.451762/info, anomalous 0.540229/medium, zero-duration 0.458718/info),
  batch (2-count and empty), and three invalid-input 422s: PASS.
- RAG status (697 docs, 384-dim) and grounded query (T1595, T1016.001, …), blank-query 422: PASS.
- Mock `/explain` (provider `mock`, technique IDs ⊆ retrieved set): PASS.
- Report generate + `%PDF-` download, malformed/unknown-ID 404s: PASS.
- Backend suite: 132 passed (87 unit + 45 integration).
