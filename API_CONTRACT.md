# Backend API Contract

**Status:** Implemented and verified 2026-09-15

This document describes the stable FastAPI contract exposed by the backend. It intentionally excludes future MITRE ATT&CK, RAG, LLM, frontend, and live-capture implementations.

## Base API

- Base path: `/api/v1`
- JSON request and response bodies
- Optional request correlation header: `X-Correlation-ID`
- Interactive documentation: `/docs`
- OpenAPI document: `/openapi.json`

## Endpoints

| Method | Endpoint | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | None | `HealthResponse` |
| `POST` | `/api/v1/detect` | `NetworkFlowRequest` | `DetectionResponse` |
| `POST` | `/api/v1/detect/batch` | `BatchDetectionRequest` | `BatchDetectionResponse` |

## Health

`GET /api/v1/health` reports application/model readiness.

```json
{
  "status": "healthy",
  "model_status": "ready",
  "model_version": "isolation_forest_v1",
  "experiment_id": "with_port",
  "active_operating_point": "OP-A",
  "active_threshold": 0.521919,
  "timestamp": "2026-09-15T12:00:00+00:00"
}
```

When artifacts are unavailable, the application reports `status: "degraded"` and `model_status: "not_loaded"`.

## Single Detection

`POST /api/v1/detect` accepts one CICIDS-style network flow. The request uses the exact feature aliases in `backend/app/schemas/detection.py`. The frozen E2 contract contains 60 features, with `Is_Zero_Duration` computed by the service when omitted. All values must be finite numbers and extra fields are rejected.

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
    "anomaly_score": 0.612345,
    "threshold": 0.521919,
    "experiment_id": "with_port",
    "operating_point": "OP-A"
  },
  "severity": {
    "level": "medium",
    "risk_score": 0.612345,
    "calibration_note": "INITIAL PLACEHOLDER CALIBRATION"
  },
  "attack_context": {
    "mitre_techniques": [],
    "retrieved_context": []
  },
  "explanation": {
    "summary": null,
    "reasoning": null,
    "recommendations": []
  },
  "metadata": {
    "model_version": "isolation_forest_v1",
    "source_dataset": "CICIDS2017",
    "timestamp": "2026-09-15T12:00:00+00:00"
  }
}
```

`anomaly_score` is computed as `-model.score_samples()`, so higher values are more anomalous. `is_anomaly` is true when the score is greater than or equal to the active frozen threshold.

The current response does not include a standalone `detected_features` attribution field because no explanation layer exists yet.

## Batch Detection

`POST /api/v1/detect/batch` accepts:

```json
{
  "flows": [
    { "Destination Port": 80, "Flow Duration": 10 }
  ]
}
```

The abbreviated flow above is illustrative only; every flow must contain the complete `NetworkFlowRequest` contract.

Response shape:

```json
{
  "batch_id": "batch-123",
  "count": 1,
  "results": [
    {
      "request_id": "batch-123-0",
      "detection": {},
      "severity": {},
      "attack_context": {},
      "explanation": {},
      "metadata": {}
    }
  ],
  "timestamp": "2026-09-15T12:00:00+00:00"
}
```

Results preserve input order. An empty `flows` list returns HTTP 200 with `count: 0` and `results: []`.

## Error Contract

All application errors use `ErrorResponse`:

```json
{
  "error_code": "INVALID_INPUT",
  "message": "Request validation failed. Verify input features and numeric constraints.",
  "details": { "validation_errors": [] },
  "timestamp": "2026-09-15T12:00:00+00:00",
  "request_id": "request-123"
}
```

| Error code | HTTP status | Meaning |
| --- | ---: | --- |
| `INVALID_INPUT` | 422 | Invalid request data, including missing, non-numeric, NaN, Infinity, or extra fields |
| `FEATURE_MISMATCH` | 422 | Feature contract or preprocessing configuration mismatch |
| `MODEL_NOT_READY` | 503 | Model or preprocessing artifact is unavailable or invalid |
| `INFERENCE_ERROR` | 500 | Preprocessing or model scoring failed |
| `INTERNAL_ERROR` | 500 | Unexpected server failure |

Inference exception details are logged internally and are not included in the API message.

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

Verified 2026-09-15:

- 39 backend tests passed, 0 failed.
- Maximum frozen fixture score difference: `0.0`.
- Threshold match: `True`.
- Prediction match: `True`.
- Health, detection, batch, `/docs`, and `/openapi.json`: PASS.
