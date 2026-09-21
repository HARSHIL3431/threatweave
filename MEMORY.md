# MEMORY.md — Project Memory (Authoritative)

**Current phase**: PHASE 4 — Backend ML Serving Foundation
**Status**: Backend serving foundation, hardening, and documentation complete (2026-09-15)
**Next phase**: Frontend

---

## Where things stand

- **Dataset**: `data/combined/CICIDS2017_COMBINED_RAW.csv` (2,830,743 × 81). All 8 CICIDS2017 days integrated, checksummed, EDA'd and audited.
- **Preprocessing**: frozen 15-stage leakage-safe pipeline in `scripts/preprocess.py` (spec: `reports/FINAL_PREPROCESSING_DESIGN.md`). Validation gate 23 PASS / 3 WARN / 0 FAIL.
- **Split**: Monday=train / Tuesday=validation / Wed–Fri=six test sets (`ML_SPLIT_STRATEGY.md`). Test sets evaluated exactly once per operating point.
- **Experiments E1/E2**: complete. Contamination candidates fitted on TRAIN, selected on VAL (max F1, tie-break min FPR — decision D011). Dual frozen operating points OP-A/OP-B (D012).
- **Reproducibility**: `python scripts/verify_reproducibility.py` → 12/12 PASS; scores float32-exact on reload.

## Key numbers (from artifacts — see FINAL_ML_REPORT.md for all)

| | E1 no port | E2 with port |
|:---|:---|:---|
| Features | 59 | 60 |
| Contamination | 0.001 | 0.10 |
| OP-A offset threshold | 0.657668 | 0.521919 |
| OP-B val-swept threshold | 0.482296 (val F1 0.110) | 0.487850 (val F1 0.123) |
| Pooled test F1 (OP-B) | 0.6123 (R=0.895, FPR=0.318) | 0.5858 (R=0.716, FPR=0.256) |
| Pooled test F1 (OP-A) | 0.0005 | 0.6264 (FPR=0.132) |
| Day PR-AUC range | 0.006–0.849 | 0.003–0.861 |

## Selected baseline

Both models FROZEN (D013): **E2 = primary detector artifact**, **E1 = behavioral-only reference/ablation**.
Reason: E2 dominates score-ranking where port encodes attack family (PortScan PR-AUC 0.51 vs 0.03); volumetric DoS/DDoS detection is port-independent; E1 documents how much of E2's edge is shortcut-based.

## Important findings

1. Contamination-offset thresholds do not transfer across days (Monday quantile ≠ later-day quantiles; drift inflates benign scores up to FPR 42% on the DDoS day at OP-A for E2).
2. Tuesday validation tuning degenerated legitimately: its only attacks (Patator, 9,152 rows) are invisible at every grid point (all F1=0.0000 for E1).
3. Per-flow unsupervised detection works for floods only: DoS families 0.63–0.99 recall; Patator/Bot/Web/Infiltration ≤ ~0.3 at usable precision.
4. False positives are structured: long-idle background service flows (443/80/53/123/88/389/445), rare in Monday's training sample.
5. Destination Port acts as a shortcut, decisive only for port-scan ranking.

## Known limitations

- Single-day (Monday) benign training; drift handling out of scope.
- E1/E2 row sets differ via pre-split dedup (documented comparability caveat).
- Tiny classes (Heartbleed n=11, SQLi n=21, Infiltration n=36) not statistically meaningful.
- No per-feature explanation layer: `detected_features` contract field NOT AVAILABLE YET.

## Artifact paths

- Models + metadata: `data/processed/experiments/baseline_no_port/model.pkl`, `data/processed/experiments/with_port/model.pkl`
- Preprocessing configs: same folders, `preprocessing_config.json`
- Results: same folders, `results.json`; saved scores under `scores/`
- Analysis: `data/processed/analysis/` (analysis_summary.json, comparison tables, sweeps, FP profiles)
- Figures: `figures/ml/fig1..fig9*.png`
- Logs: `scripts/run_all_log.txt`, `scripts/analysis_log.txt`, `scripts/fp_analysis_log.txt`, `scripts/reproducibility_log.txt`

## Backend handoff

Contract: `reports/ML_BACKEND_HANDOFF.md`. Backend receives per-flow
`{is_anomaly, anomaly_score, threshold, model_version, experiment_id,
detected_features(NOT AVAILABLE YET), source_dataset, timestamp}` plus the exact
input schema/order from artifact metadata. Thresholds are policy constants —
no runtime mutation API.

## Backend implementation status

- FastAPI E2 serving path is implemented at `/api/v1/health`, `/api/v1/detect`,
	and `/api/v1/detect/batch`; the model loads once through application lifespan.
- Backend preprocessing reads E2 `feature_names`, `log1p_features`, and
	`signed_log_features` from `preprocessing_config.json` and validates them
	against model metadata before readiness.
- Zero-duration inference matches `scripts/preprocess.py`: add the flag, clip
	duration to 1 microsecond, recompute rates, then transform and order features.
- Backend test suite: 39 passed, 11 warnings on 2026-09-15, including corrupt
	artifact handling, safe inference errors, frozen ML score/prediction
	consistency, and OpenAPI route checks.
- Inference failures return generic structured `INFERENCE_ERROR` responses;
	internal exception details are retained only in logs.
- Backend documentation is maintained in `backend/README.md`,
	`API_CONTRACT.md`, and `ARCHITECTURE.md`.

## Rules going forward

- Do not modify preprocessing, split, thresholds, or models without a NEW experiment ID.
- Update EXPERIMENTS.md / DECISIONS.md for any future run.


---

## FRONTEND PHASE COMPLETE (2026-09-20)

### Frontend Implementation Status

**Project Structure:**
- `frontend/` - Complete React TypeScript frontend with modular architecture
- Technology: React 18, TypeScript, Vite, Tailwind CSS, Framer Motion
- State Management: React Query + Zustand
- API Layer: Typed Axios client with error handling

**Implemented Features:**

1. **Interactive Landing Page**
   - SystemPipelineDemo component showing ML workflow visualization
   - Animated demonstration of: Raw Flow → Processing → Detection → Score → Severity → Intelligence → Report
   - Smooth scrolling transitions and component animations
   - Sample flow selection with real backend integration

2. **Security Dashboard**
   - Real-time system health monitoring
   - StatsOverview with modular card components
   - Model information display
   - Placeholders for future analytics

3. **Network Flow Detection**
   - FlowInput component with simple/advanced modes
   - Sample flow selection from CICIDS2017 fixtures
   - Real backend API integration (`POST /api/v1/detect`)
   - ResultDisplay with ScoreIndicator visualization
   - Severity classification display
   - Future intelligence section placeholders

4. **Modular Architecture**
   - Replaceable component boundaries for easy UI updates
   - Separate animation components (ScrollReveal, SectionTransition)
   - Separate visualization components (ScoreIndicator)
   - Feature-based organization
   - Clear separation of business logic and presentation

**Key Frontend Numbers:**
- Components: 45+ modular, replaceable components
- Pages: 4 complete pages (Landing, Dashboard, Detection, NotFound)
- API Endpoints: 2 fully integrated (/health, /detect)
- Animations: 6+ custom animation presets
- Responsive breakpoints: 4 (sm, md, lg, xl)

**Integration Status:**
- ✅ Backend running on port 8001 (E2 Isolation Forest)
- ✅ Frontend proxy configured to port 8001
- ✅ Health endpoint integration working
- ✅ Detection endpoint integration working
- ✅ Sample flow validation working
- ✅ Error handling and loading states implemented

**Visual Design:**
- Cybersecurity-focused color palette
- Professional spacing and typography
- Smooth animations with Framer Motion
- Glass effects and gradients
- Responsive design for desktop, tablet, mobile
- Accessibility considerations (keyboard nav, ARIA labels)

**Development Guidelines Followed:**
1. Inspect before changing - verified backend schemas
2. Reuse existing work - used backend sample fixtures
3. Backend is frozen - no ML model changes
4. Backend is source of truth - display actual API results
5. No fabricated ML/intelligence results
6. Modular, replaceable component architecture
7. Separate animation logic from business logic
8. Clear component boundaries for future UIverse/Motion integrations

**Next Recommended Task:**
Implement comprehensive testing suite including:
1. Component unit tests with Jest/React Testing Library
2. Integration tests for API layer
3. E2E tests for critical user journeys
4. Performance testing for animation-heavy components
5. Accessibility audit for WCAG compliance

**Frontend Artifacts:**
- Source code: `frontend/src/`
- Configuration: `frontend/package.json`, `vite.config.ts`, `tailwind.config.js`
- Documentation: `frontend/README.md`
- Environment: `frontend/.env`, `frontend/.env.example`
- Sample data: `frontend/src/data/sampleFlows.ts`

**Rules Going Forward:**
- Frontend component architecture supports easy replacement
- Animation components are modular and replaceable
- API layer provides typed interfaces matching backend
- All visual components have clear prop boundaries
- Business logic is separated from presentation
- Future UIverse/Motion component integrations will be straightforward