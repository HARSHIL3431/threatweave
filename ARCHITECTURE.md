# Backend Architecture

**Status:** Backend ML-serving foundation complete and verified 2026-09-15

## Scope

The backend scores individual CICIDS2017-style network flows with the frozen E2 Isolation Forest detector. It owns request validation, per-flow preprocessing, inference, severity classification, and structured responses.

It does not currently implement MITRE ATT&CK ingestion, RAG retrieval, embeddings, vector storage, LLM integration, React, live packet capture, or retraining.

## Component Flow

```text
                  +----------------------+
                  | React Frontend       |
                  | Future               |
                  +----------+-----------+
                             |
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
                  +----------+----------+----------+
                  v                     v          v
               MITRE                 RAG        LLM
               Future                Future     Future
```

## Application Lifecycle

`app.main` creates the FastAPI application and uses a lifespan handler to load one `MLService` instance at startup. The service loads:

- `data/processed/experiments/with_port/model.pkl`
- `data/processed/experiments/with_port/preprocessing_config.json`

The feature contract and configured transformations are validated against model metadata before the service is marked ready. Health can still report a degraded application when startup loading fails.

## API Boundary

Routes are intentionally thin:

- `app/api/v1/health.py` exposes model/application readiness.
- `app/api/v1/detection.py` accepts validated single-flow and batch requests.
- `app/api/v1/router.py` mounts the v1 routes.

Request and response types are defined in `app/schemas/`. Application exceptions are converted to `ErrorResponse` by handlers in `app/main.py`.

## Service Responsibilities

### DetectionService

Coordinates the request workflow:

1. Convert the validated Pydantic request to the feature-alias dictionary.
2. Call `MLService` for detection.
3. Call `SeverityService` for risk classification.
4. Call the future-service stubs for attack context, retrieval context, and explanation.
5. Assemble the stable detection response.

### MLService

Owns the frozen detector boundary:

- Load and validate the model and preprocessing artifacts.
- Load the authoritative E2 feature order and transform lists.
- Handle zero-duration flows.
- Apply configured `log1p` and signed-log transformations.
- Produce the exact ordered NumPy matrix.
- Compute `-model.score_samples(X)`.
- Apply the selected frozen operating point.

ML decides whether traffic is anomalous. It does not produce explanations or MITRE context.

### SeverityService

Maps the anomaly score to the current placeholder severity tiers:

- Critical: score `>= 0.80`
- High: score `>= 0.65`
- Medium: score `>= active threshold`
- Low: score `>= active threshold * 0.90`
- Info: below that low boundary

This is explicitly **INITIAL PLACEHOLDER CALIBRATION**, not a validated risk model.

### MitreService

Future extension point for MITRE ATT&CK context. It currently returns an empty list by default.

### RagService

Future extension point for knowledge retrieval and playbooks. It currently returns an empty list by default.

### LLMService

Future extension point for explanations and recommendations. It currently returns an empty explanation by default.

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

Dataset-level operations are outside this boundary. The API does not load the combined dataset, repair labels, remove conflicts, deduplicate, split by source day, retrain, or tune thresholds.

The model score semantics are:

```python
anomaly_score = -model.score_samples(X.values)
is_anomaly = anomaly_score >= threshold
```

Therefore, higher scores are more anomalous.

## Configuration Boundary

Configuration is provided by environment variables or `.env`:

- `MODEL_PATH`
- `PREPROCESSING_CONFIG_PATH`
- `ACTIVE_OPERATING_POINT`
- `APP_ENV`
- `LOG_LEVEL`
- `API_VERSION`
- `ALLOWED_ORIGINS`
- `MITRE_ENABLED`
- `RAG_ENABLED`
- `LLM_ENABLED`

`ACTIVE_OPERATING_POINT` accepts only `OP-A` or `OP-B`. No endpoint mutates this policy at runtime.

## Error Boundary

The application exposes structured errors with these codes:

- `INVALID_INPUT`
- `FEATURE_MISMATCH`
- `MODEL_NOT_READY`
- `INFERENCE_ERROR`
- `INTERNAL_ERROR`

Detailed inference failures are logged internally. The API returns only the generic `INFERENCE_ERROR` message so model internals, paths, and secrets are not disclosed.

## Current Structure

```text
backend/
├── .env.example
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── health.py
│   │       └── detection.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── detection.py
│   │   └── health.py
│   └── services/
│       ├── __init__.py
│       ├── ml_service.py
│       ├── detection_service.py
│       ├── severity_service.py
│       ├── mitre_service.py
│       ├── rag_service.py
│       └── llm_service.py
└── tests/
  ├── __init__.py
  ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    ├── unit/
    └── integration/
```

## Verification Boundary

The backend was verified on 2026-09-15 with 39 passing tests and 0 failures. The frozen consistency fixtures produced maximum score difference `0.0`, with threshold and prediction matches both `True`. Health, single detection, batch detection, Swagger, and OpenAPI checks passed.
