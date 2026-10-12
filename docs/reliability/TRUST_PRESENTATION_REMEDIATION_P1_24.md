# Trust Presentation Remediation P1-24 (DI-007 + DI-008)

Copy-only remediation: no detector, retrieval, guard, threshold, label,
baseline, contract, or dependency changed. No calibrated probability was
manufactured; nothing is claimed calibrated.

## 1. Confirmed issues and fixes (before → after)

1. **Landing "F1-validated Model (E2)"** (`frontend/src/components/landing/hero.tsx:34`).
   Before implied independently validated F1. Evidence (DI-005): same-lab
   descriptive metrics only — test-only pooled OP-A F1 0.6264 / OP-B
   0.5858, no disjoint-lineage generalization. After: **"Lab-measured F1
   (E2)"**.
2. **Landing "Network Flows Analyzed"** (`hero.tsx:32`). 2.83M is the
   verified combined-dataset row count (2,830,743), but "Analyzed" in a
   product hero implies product work. After: **"Dataset Network Flows"**
   (value and "CICIDS2017 Dataset" caption unchanged).
3. **"Engineered & Validated" features caption** (`hero.tsx:33`). After:
   **"Frozen Feature Contract"** (matches the frozen E2 60-feature
   contract; no validation claim).
4. **"Risk-based severity" demo copy ×2** (`frontend/src/lib/data/demoFlows.ts:156,166`).
   Evidence (P1-10): severity derives from score bands only;
   `risk_score` is byte-identical to `anomaly_score` under a placeholder
   note — zero risk modeling exists. After: **"Score-based severity"**.
5. **Unlabeled landing mock** (`frontend/src/components/landing/mitre-ai.tsx`):
   concrete score 0.87, HIGH severity, "High Confidence" badge, and
   "Matches known exfiltration behavior" with no sample labeling. After:
   section carries **"Illustrative mock preview — scores, severity, and
   confidence shown are placeholders, not backend output."**
6. **`ConfidenceBadge` ("{level} Confidence")** (`frontend/src/components/ui/confidence-badge.tsx`):
   bare calibrated-sounding label, currently used in mock/sample/landing
   surfaces only (verified: no live-path usage). After: same text plus
   `title="Similarity-based candidate qualifier — not calibrated
   confidence"` (layout, interactions, theming untouched).
7. **Sample PDF confidence wording** (`frontend/src/lib/report.ts`, SAMPLE path only):
   `(High confidence)` → `(High similarity-based confidence)`;
   `Confidence` kv → `Confidence (similarity band)`; related-technique
   confidence likewise qualified. SAMPLE banner and candidate disclaimer
   retained.
8. **Backend PDF "probabilistic"** (`backend/app/services/report_service.py:425`):
   scores are uncalibrated ranking values, not probabilities (P1-10 §4.5).
   After: **"Anomaly detection is statistical. … candidate for review …"**
   (second clause untouched, so the pinned "candidate for review"
   assertion still holds).
9. **Backend PDF technique-table header "Confidence"** (`report_service.py:359`):
   values are similarity bands / model assertions about candidates. After:
   **"Candidate confidence"** (section title "Potential Attack Context
   (candidates only)" unchanged).

## 2. Verified honest, left unchanged

Live detection page (LIVE badge, candidate-for-review note, calibration
note echo), live-workflow explanation (candidate-only framing ×2),
MITRE page (grounded-candidates disclaimer, similarity "score",
provenance honesty incl. stale/unknown), Gauge ("Anomaly Score
(uncalibrated)", dial-capped caption), gauge-scale helper, charts,
dashboard/analytics "placeholder severity bands" captions, mock-branch
SAMPLE banners + honest severity caption, `modelAccuracy: "94.7%"` (dead
data, never rendered — no UI impact), backend "Anomaly Score
(Uncalibrated)" label, "not human-reviewed" disclaimer.

## 3. Tests and validation

- Backend: `test_report_service.py` extended (rejects "probabilistic",
  asserts "statistical"; asserts "Candidate confidence" header with
  whitespace-flattened extraction). Focused report suites 47/47.
- Frontend: `npx tsc --noEmit` clean; `npx eslint` on all five changed
  files clean; full `npm run build` (Next.js 16.3.8 Turbopack: compile +
  TypeScript + 11 static pages) succeeds.
- No browser/E2E verification run — not claimed.
- Full backend suite run post-change (see final report).

## 4. Remaining owner/data work (DI-007, DI-008 stay open)

Calibration study (labeled explanation-correctness data, proper scoring,
family stratification — DI-007 acceptance), operator-interpretation study
(DI-008 acceptance), family-aware severity research, per-family
precision disclosure in UI (proposed, not implemented), real-model
confidence semantics (model-asserted enums remain free assertions).
Labels and disclaimers do not calibrate anything.

## 5. Regression risks

Wording-only changes; layout/keys/contracts untouched. PDF header width
(20 mm) wraps the longer header across two lines (VALIGN TOP; asserted
in test). `title` tooltips are hover-only — screen-reader and touch
users rely on surrounding mock captions, which are present at every usage
site.
