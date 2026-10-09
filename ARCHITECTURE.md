# Backend Architecture

**Status:** Backend ML-serving, RAG, explanation, and reporting layers complete and verified 2026-10-09
(backend suite 132 passed: 87 unit + 45 integration)

## Scope

The backend scores individual CICIDS2017-style network flows with the frozen E2 Isolation Forest detector,
retrieves MITRE ATT&CK context from a local FAISS knowledge base, produces grounded structured LLM
explanations on demand, and generates server-side PDF incident reports. It owns request validation, per-flow
preprocessing, inference, severity classification, retrieval, explanation validation, and report rendering.

It does not currently implement live packet capture, retraining, or **server-side detection-history
persistence** — there is no database and no record-listing endpoint. Analysis is stateless per request;
the only server-persisted artifacts are generated PDFs (by UUID) and the prebuilt FAISS index.

## Component Flow

```text
                  +----------------------+
                  | Next.js Frontend     |
                  | /api/* rewrite       |
                  | Browser session store|
                  +----------+-----------+
                              | /api/v1/* (proxied to :8001)
                              v
                  +----------------------+
                  | FastAPI /api/v1      |
                  +----------+-----------+
                              |
                              v
                  +----------------------+
                  | Pydantic Validation  |
                  +----------+-----------+
                              |
                              v
                  +----------------------+
                  | DetectionService     |
                  +----------+-----------+
                              |
                              v
                  +----------------------+
                  | MLService            |
                  | Frozen E2 Isolation   |
                  | Forest               |
                  +----------+-----------+
                              |
                              v
                  +----------------------+
                  | Anomaly + Severity   |
                  +----------+-----------+
                              |
              +---------------+---------------+
              v               v               v
      MitreService      RagService      LLMService
      (retrieval-       (FAISS MITRE    (openai/mock,
       based IDs)        ATT&CK)         /explain only)
              |               |               |
              +-------+-------+               |
                      v                       v
              AnalysisEvidence        validated output
                      |                       |
                      +-----------+-----------+
                                  v
                           ReportService
                           (server-side PDF)
```

## Application Lifecycle

`app.main` creates the FastAPI application and uses a lifespan handler to load one `MLService` instance at
startup. The service loads:

- `data/processed/experiments/with_port/model.pkl`
- `data/processed/experiments/with_port/preprocessing_config.json`

The feature contract and configured transformations are validated against model metadata before the service
is marked ready. Health can still report a degraded application when startup loading fails. RAG index loading
is best-effort and never blocks startup: if the MITRE index is missing, a warning is logged and ML detection
remains fully functional.

## API Boundary

Routes are intentionally thin (mounted under `/api/v1` by `app/api/v1/router.py`):

- `app/api/v1/health.py` exposes model/application readiness plus RAG index state.
- `app/api/v1/detection.py` accepts validated single-flow and batch requests.
- `app/api/v1/rag.py` exposes index status and grounded technique search.
- `app/api/v1/explain.py` re-runs the pipeline and returns a validated structured LLM explanation.
- `app/api/v1/reports.py` generates server-side PDFs and streams downloads by UUID.

Request and response types are defined in `app/schemas/`. Application exceptions are converted to
`ErrorResponse` by handlers in `app/main.py`. Full method/path/schema details live in `API_CONTRACT.md`.

## Service Responsibilities

### DetectionService

Coordinates the request workflow:

1. Convert the validated Pydantic request to the feature-alias dictionary.
2. Call `MLService` for detection.
3. Call `SeverityService` for risk classification.
4. Call `MitreService` for technique IDs (only when `MITRE_ENABLED=true`) and `RagService` for retrieved
   context (only when `RAG_ENABLED=true`); both degrade to empty lists without blocking detection.
5. Attach the (intentionally empty) detection-flow explanation hook output.
6. Assemble the stable detection response.

### MLService

Owns the frozen detector boundary:

- Load and validate the model and preprocessing artifacts.
- Load the authoritative E2 feature order and transform lists.
- Handle zero-duration flows.
- Apply configured `log1p` and signed-log transformations.
- Produce the exact ordered NumPy matrix.
- Compute `-model.score_samples(X)`.
- Apply the selected frozen operating point.

ML decides whether traffic is anomalous. It does not produce explanations or confirm MITRE techniques.

### SeverityService

Maps the anomaly score to the current placeholder severity tiers:

- Critical: score `>= 0.80`
- High: score `>= 0.65`
- Medium: score `>= active threshold`
- Low: score `>= active threshold * 0.90`
- Info: below that low boundary

This is explicitly **INITIAL PLACEHOLDER CALIBRATION**, not a validated risk model.

### MitreService

Retrieval-based mapping only. The frozen model cannot confirm attack techniques, so for anomalous flows the
service builds a descriptive query from flow characteristics and returns potentially *relevant* technique IDs
taken exclusively from the grounded index. Gated by `MITRE_ENABLED` (default `false`); returns `[]` otherwise,
when the flow is benign, or when RAG is unavailable. Every ID is a candidate, never a confirmed detection.

### RagService

Retrieval over the local FAISS MITRE ATT&CK index (384-dim MiniLM embeddings, 697 documents). The index is
lazy-loaded once and cached. If it is missing, the standalone query surface returns controlled
`503 RAG_UNAVAILABLE` while detection evidence degrades to empty context. `RagService(enabled=True)` backs the
public `/rag/*` endpoints regardless of the flag; detection-time retrieval honors `RAG_ENABLED`.

### LLMService

Structured incident explanations backed by a pluggable provider (`openai` — OpenAI-compatible chat
completions over httpx — or `mock` — deterministic offline). Rules enforced in code:

- The LLM is invoked **only** through `/explain` (and attached optionally to reports). The `/detect`
  pipeline never calls it.
- Output must pass schema validation plus technique grounding (IDs ⊆ RAG results, names match, confidence
  in `low/medium/high`); violations become `LLM_VALIDATION_ERROR`.
- Missing/disabled provider or API key becomes controlled `503 LLM_UNAVAILABLE`, never a fabricated answer.
- No API keys are logged; only request metadata (request id, provider, model, latency, outcome) is logged.

### ReportService

Renders `AnalysisEvidence` (ML + severity + flow indicators + retrieved techniques + optional validated LLM
explanation) to PDF via reportlab into the controlled `REPORTS_DIR`. Filenames are server-generated UUIDs;
`report_file()` accepts only 32-hex IDs resolved strictly inside the output directory, so path traversal is
impossible. All rendered text is sanitized and XML-escaped; no keys or environment values are rendered.

## ML and Preprocessing Boundary

The backend uses the frozen primary experiment:

```text
Experiment: with_port
Features: 60
Model version: isolation_forest_v1
OP-A: 0.5219193851693676
OP-B: 0.4878500998020172
```

API inference is per-flow only:

```text
Raw flow
  -> zero-duration flag, duration floor, and rate recomputation
  -> configured log1p transformations
  -> configured signed-log transformations
  -> exact artifact feature order
  -> Isolation Forest score
  -> threshold decision
```

Dataset-level operations are outside this boundary. The API does not load the combined dataset, repair labels,
remove conflicts, deduplicate, split by source day, retrain, tune thresholds, or persist detection history.

The model score semantics are:

```python
anomaly_score = -model.score_samples(X.values)
is_anomaly = anomaly_score >= threshold
```

Therefore, higher scores are more anomalous.

## Configuration Boundary

Configuration is provided by environment variables or `.env` (see `backend/.env.example`):

- `MODEL_PATH`, `PREPROCESSING_CONFIG_PATH`
- `ACTIVE_OPERATING_POINT` (`OP-A` or `OP-B` only; no runtime mutation endpoint)
- `APP_ENV`, `LOG_LEVEL`, `API_VERSION`, `ALLOWED_ORIGINS`
- `MITRE_ENABLED`, `RAG_ENABLED`, `LLM_ENABLED` (all default `false`)
- `MITRE_DATA_DIR`, `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`
- `LLM_PROVIDER` (`openai`|`mock`), `LLM_MODEL`, `LLM_API_KEY` (never hard-code), `LLM_TEMPERATURE`,
  `LLM_TIMEOUT`, `LLM_OPENAI_BASE_URL`
- `REPORTS_DIR`

## Error Boundary

Structured `ErrorResponse` codes (`app/core/exceptions.py`; HTTP mapping in `API_CONTRACT.md`):

- `INVALID_INPUT`, `FEATURE_MISMATCH`, `MODEL_NOT_READY`, `INFERENCE_ERROR`, `INTERNAL_ERROR`
- `RAG_UNAVAILABLE`, `LLM_UNAVAILABLE`, `LLM_PROVIDER_ERROR`, `LLM_TIMEOUT`, `LLM_VALIDATION_ERROR`
- `REPORT_ERROR`, `REPORT_NOT_FOUND`

Detailed inference failures are logged internally. The API returns only generic messages so model internals,
paths, and secrets are not disclosed.

## Frontend Session Storage (no server history)

Because the backend persists no detection history, the Next.js UI keeps the user's own live
`DetectionResponse` records in browser localStorage (`threatweave.session.detections.v1`, capped, clearable;
see `frontend/src/lib/session-store.ts`). Dashboard and analytics aggregates derive solely from these
session records and are labeled as such. Session data is per-browser, never global or cross-device, and is
not a substitute for server-side persistence.

## Current Structure

```text
backend/
├── .env.example
├── requirements.txt              # includes httpx>=0.27.0,<0.28 (Starlette 0.36 TestClient compat)
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py                   # lifespan: MLService load + best-effort RAG preload
│   ├── dependencies.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── health.py
│   │       ├── detection.py
│   │       ├── rag.py
│   │       ├── explain.py
│   │       └── reports.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── detection.py
│   │   ├── health.py
│   │   ├── rag.py
│   │   ├── llm.py
│   │   └── report.py
│   └── services/
│       ├── __init__.py
│       ├── ml_service.py
│       ├── detection_service.py
│       ├── severity_service.py
│       ├── mitre_service.py
│       ├── mitre_data.py
│       ├── rag_service.py
│       ├── embedding_service.py
│       ├── vector_store.py
│       ├── llm_service.py
│       ├── llm_providers.py
│       ├── llm_prompts.py
│       ├── llm_validation.py
│       ├── analysis_evidence.py
│       └── report_service.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   └── sample_flows.json
    ├── unit/
    └── integration/
```

## Verification Boundary

Verified 2026-10-09 with 132 passing tests (87 unit + 45 integration) plus live-HTTP checks: health,
single/batch detection with exact fixture scores (benign 0.451762/info, anomalous 0.540229/medium,
zero-duration 0.458718/info), RAG status/query, mock explanation with grounded technique IDs, and report
generation plus `%PDF-` download with controlled 404s for bad identifiers.
