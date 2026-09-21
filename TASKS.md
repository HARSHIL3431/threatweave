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

## PHASE 4: Backend — COMPLETE (2026-09-15)
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
- [x] Backend API/architecture documentation (`backend/README.md`, `API_CONTRACT.md`, `ARCHITECTURE.md`)

## PHASE 5: Frontend/Dashboard — COMPLETE (2026-09-20)
- [x] Flow-scoring UI surfacing anomaly_score + threshold context (not binary alone)
- [x] Interactive landing page with system pipeline visualization
- [x] Security dashboard with real-time health monitoring
- [x] Network flow detection with sample/test modes
- [x] Modular component architecture with replaceable boundaries
- [x] Backend API integration (health + detection endpoints)
- [x] Responsive design for desktop/tablet/mobile
- [x] Animation system with Framer Motion
- [x] Professional cybersecurity visual design
- [x] Documentation and project memory updates

## BACKLOG (explicitly out of scope until backend/frontend done)
- [ ] RAG knowledge layer
- [ ] MITRE ATT&CK mapping
- [ ] LLM integration
- [ ] Explanation layer for `detected_features`
