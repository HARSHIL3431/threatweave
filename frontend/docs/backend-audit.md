# Backend Audit (P-1; routes extended since — see update note at end)

Real captures saved under `docs/evidence/` (health.json, detect-*.json, detect-batch.json, detect-error.json).

## Framework / entry / port
- FastAPI 0.110.0, host `backend/app/main.py`, run from `C:\Users\Admin\Desktop\demo\backend`:
  `uvicorn app.main:app --port 8001` (project docs default 8000; integration scripts use 8001).
- Port in use: **8001** → base URL `http://localhost:8001`. Swagger `/docs`, OpenAPI `/openapi.json`.
- CORS: `ALLOWED_ORIGINS` env, default `http://localhost:3000,http://localhost:5173` (see `.env.example`).
- No auth. MITRE/RAG/LLM services are no-op stubs, disabled by default.

## Endpoints

### GET /api/v1/health
Real response (evidence/health.json):
```json
{"status":"healthy","model_status":"ready","model_version":"isolation_forest_v1","experiment_id":"with_port","active_operating_point":"OP-A","active_threshold":0.521919,"rag_status":"ready","timestamp":"2026-10-06T15:40:31.517590+00:00"}
```

### POST /api/v1/detect
Request: full 60-feature CICIDS2017 flow JSON (aliases like `Destination Port`, `Flow Duration`, `Flow Bytes/s`); `Is_Zero_Duration` optional (computed server-side). Unknown fields → 422.
Real response (evidence/detect-benign_flow.json):
```json
{
  "request_id": "c3c971a4-47d3-4b69-a78c-30bdf1b5e347",
  "detection": {"is_anomaly": false, "anomaly_score": 0.451762, "threshold": 0.521919, "experiment_id": "with_port", "operating_point": "OP-A"},
  "severity": {"level": "info", "risk_score": 0.451762, "calibration_note": "INITIAL PLACEHOLDER CALIBRATION"},
  "attack_context": {"mitre_techniques": [], "retrieved_context": []},
  "explanation": {"summary": null, "reasoning": null, "recommendations": []},
  "metadata": {"model_version": "isolation_forest_v1", "source_dataset": "CICIDS2017", "timestamp": "..."}
}
```
Sample scores: benign 0.451762/info, anomalous 0.540229/medium(is_anomaly true), zero-duration 0.458718/info.
Severity mapping: critical >=0.80, high >=0.65, medium >= threshold(0.521919), low >= threshold*0.90, info below.

### POST /api/v1/detect/batch
`{"flows": [...]}` → `{"batch_id", "count", "results": [...same shape...], "timestamp"}` (evidence/detect-batch.json).

### Errors
422 INVALID_INPUT shape (evidence/detect-error.json): `{"detail": [...]}` for pydantic validation; app error shape `{"error_code","message","details","timestamp","request_id"}`. Codes: INVALID_INPUT(422), FEATURE_MISMATCH(422), MODEL_NOT_READY(503), INFERENCE_ERROR(500), INTERNAL_ERROR(500).

## Feature gaps vs UI spec
- No history/stats/KPI/chart endpoints, no detections list, no technique mapping, no feature importance, no PDF/report generation, no CSV upload endpoint. These UI needs have no backend source → SAMPLE/derived via adapters; feature-map.md tracks.
- `POST /api/v1/detect` (and batch) are stateless scoring calls — safe to call from UI adapters and smoke tests.

## Update 2026-10-09 (supersedes the P-1 endpoint claims above)
- The backend now exposes 8 routes — the P-1 "only health + detect" finding is obsolete. Added since:
  `GET /api/v1/rag/status`, `POST /api/v1/rag/query` (FAISS MITRE ATT&CK, 697 docs), `POST /api/v1/explain`
  (validated, grounded LLM via `openai`/`mock`), `POST /api/v1/reports/generate` and
  `GET /api/v1/reports/{id}/download` (server-side PDFs). Authoritative contract: root `API_CONTRACT.md`.
- Error codes now also include `RAG_UNAVAILABLE` (503), `LLM_UNAVAILABLE` (503), `LLM_PROVIDER_ERROR` (502),
  `LLM_TIMEOUT` (504), `LLM_VALIDATION_ERROR` (502), `REPORT_ERROR` (500), `REPORT_NOT_FOUND` (404).
- Still no detection-history persistence (no database, no listing endpoint) — dashboard/analytics history is
  the browser session store (`src/lib/session-store.ts`). Technique mapping and feature importance remain
  unavailable by design (candidates only / not fabricated).
