# TASKS.md — Task Tracker (Authoritative)

## PHASE 1–2: EDA & Data Foundation — COMPLETE
- [x] Individual EDA for all 8 datasets
- [x] EDA audit (16/18 claims verified)
- [x] Combined dataset integration (2,830,743 × 81)
- [x] Combined EDA + drift analysis
- [x] Cross-dataset duplicate analysis (309,079 dups, 697 conflicts)
- [x] Leakage audit (4 vectors identified & closed)
- [x] Feature redundancy analysis

## PHASE 3: ML Detection Layer — COMPLETE (2026-08-22)
- [x] Preprocessing design audit + implementation (`scripts/preprocess.py`)
- [x] Pre-experiment validation gate (23 PASS / 3 WARN / 0 FAIL)
- [x] Fix contamination-tuning methodology (fit on train, select on val — D011)
- [x] Run full E1 experiment (59 features) — artifacts saved
- [x] Run full E2 experiment (60 features) — artifacts saved
- [x] Contamination tuning on validation only; grids recorded
- [x] Threshold selection on validation only; OP-A/OP-B frozen (D012)
- [x] Per-day evaluation (6 test sets × 2 experiments × 2 operating points)
- [x] Attack-wise breakdown (12 attack classes, OP-A + OP-B)
- [x] Benign false-positive analysis (per split + feature/port profiling)
- [x] Figures 1–9 in `figures/ml/`
- [x] Model artifacts with provenance metadata; reload verified
- [x] Reproducibility check 12/12 PASS
- [x] FINAL_ML_REPORT.md (actual numbers only)
- [x] ML_BACKEND_HANDOFF.md (frozen I/O contract)
- [x] Baseline freeze (D013); MEMORY/EXPERIMENTS/DECISIONS/status updated

## PHASE 4: Backend — COMPLETE (2026-09-15), extended afterwards
- [x] FastAPI service skeleton loading frozen model artifacts
- [x] `/api/v1/detect` and `/api/v1/detect/batch` endpoints implementing the handoff response
- [x] Input validation for missing, extra, non-numeric, NaN, and Infinity values
- [x] Batch scoring + response schema incl. `detected_features: NOT AVAILABLE YET` handling
- [x] Config: model path, active operating point (OP-A vs OP-B policy)
- [x] Artifact-driven E2 feature order and transform-list validation
- [x] Zero-duration inference behavior verified against `scripts/preprocess.py`
- [x] OpenAPI route verification and frozen ML consistency test
- [x] Dedicated corrupt-artifact, malformed-config, and inference-failure tests
- [x] Structured error responses verified without internal detail leakage
- [x] MITRE ATT&CK retrieval service (FAISS, 697 docs, 384-dim) + `/api/v1/rag/status`, `/api/v1/rag/query`
- [x] Grounded LLM explanation layer (`openai`/`mock` providers) + `/api/v1/explain` with schema + technique-grounding validation
- [x] Server-side PDF reports + `/api/v1/reports/generate`, `/api/v1/reports/{id}/download` with UUID-scoped, traversal-safe access
- [x] Backend API/architecture documentation (`backend/README.md`, `API_CONTRACT.md`, `ARCHITECTURE.md`)
- [x] Test-env fix: `httpx>=0.27.0,<0.28` pin (Starlette 0.36 `TestClient` passes `app=`, removed in httpx 0.28); suite green: 132 passed (87 unit + 45 integration)

## PHASE 5: Frontend/Dashboard — COMPLETE (2026-09-20), extended afterwards
- [x] Flow-scoring UI surfacing anomaly_score + threshold context (not binary alone)
- [x] Interactive landing page with system pipeline visualization
- [x] Security dashboard with real-time health monitoring
- [x] Network flow detection with sample/test modes
- [x] Backend API integration (health + detection + RAG + explain + reports)
- [x] Live RAG-backed MITRE ATT&CK search page
- [x] Live detection → grounded explanation → backend-PDF workflow (Reports page)
- [x] Browser-session detection store (localStorage; backend persists no history) backing dashboard/analytics metrics with labeled empty states
- [x] Sample/demo content labeled SAMPLE/DEMO; no mock data presented as live
- [x] Responsive design for desktop/tablet/mobile
- [x] Documentation and project memory updates

## PHASE 6: End-to-end verification — COMPLETE (2026-10-09, PASS WITH LIMITATIONS)
- [x] Frozen-model identity (E2 `with_port`, 60 features, OP-A 0.521919) and exact fixture scores verified over HTTP
- [x] All 8 routes exercised (health, detect, batch, RAG status/query, explain, report generate/download) incl. controlled 422/404/503 paths
- [x] Mock-provider grounding verified (technique IDs ⊆ retrieved context); real external LLM explicitly NOT tested (no key)
- [x] Frontend tsc/lint/build green; backend 132/132; manual browser E2E (detection, explanation, PDF, MITRE search) passed
- [x] Report: `THREATWEAVE_PHASE6_FINAL_AUDIT.md`
- [ ] Real-provider LLM evaluation (requires approved key) — open
- [ ] Server-side detection-history persistence (new contract; requires approval) — open, proposed only

## BACKLOG (remaining, needs approval before implementation)
- [ ] Server-side detection-history persistence + listing endpoint (dashboard/analytics currently use the browser session store)
- [ ] Per-feature explanation layer for `detected_features`
- [ ] Calibrated severity/risk model to replace the placeholder bands

(End of file - total 66 lines)
