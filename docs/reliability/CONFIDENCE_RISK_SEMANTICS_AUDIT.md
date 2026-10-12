# Confidence, Risk, Severity & Score Semantics Audit (P1-10)

Inventory of every confidence/risk/score/severity value, traced
source-to-consumer, with supported vs unsupported interpretations. Observed
implementation behavior and measured evaluation results are facts;
recommendations are labeled as such.

## 1. Complete value inventory

| # | Value | Source → calculation | Range / direction | Kind | Supported interpretation |
|---|---|---|---|---|---|
| 1 | `anomaly_score` | `MLService.predict`: `-score_samples(X)[0]`, float64 | Observed 0–0.69 in evaluated data; unbounded in principle; higher = more anomalous | Uncalibrated ranking score | Relative anomalousness only |
| 2 | `is_anomaly` | `score >= active_threshold` (OP-A `0.5219193851693676` default; OP-B `0.4878500998020172` startup-selectable) | Boolean | Thresholded decision | Flag for review at the frozen operating point |
| 3 | `threshold` | Active operating point, echoed rounded to 6dp | Fixed per deployment | Frozen constant | Decision boundary reference |
| 4 | `severity.level` | `SeverityService`: critical ≥0.80; high ≥0.65; medium ≥threshold; low ≥0.9×threshold; info below | 5 ordinals | Mixed heuristic: critical/high are **absolute** score bands; medium/low/info are **threshold-relative** | Anomaly-magnitude band + decision echo; NOT impact, NOT confidence |
| 5 | `risk_score` | `round(score, 6)` — **byte-identical to `anomaly_score`** (pinned by test) | Same as #1 | Renamed score under `INITIAL PLACEHOLDER CALIBRATION` | Nothing beyond #1; the name is misleading, the note admits it |
| 6 | `calibration_note` | Constant `"INITIAL PLACEHOLDER CALIBRATION"` | Fixed string | Honesty label | Placeholder disclaimer, always present |
| 7 | Technique `confidence` (low/medium/high) | Mock: cosine cutoffs 0.55/0.45; real LLM: model-asserted enum | 3 labels | Similarity band (mock) / free assertion (LLM) | Candidate qualifier only; never a probability |
| 8 | RAG `score` | FAISS inner product on normalized embeddings = cosine, 6dp (4dp in prompts) | Roughly 0.08–0.73 observed | Similarity | Retrieval ordering only |
| 9 | Dashboard aggregates | Session counts, severity mix, score trend | Counts | Descriptive session statistics | "What I scored in this browser", honestly captioned |
| 10 | Mock fixture values | Hardcoded dev data (`USE_MOCK`, sample pages/PDF) | Fixed | UI preview only | Nothing; SAMPLE-badged |

No probability, likelihood percentage, or calibrated confidence exists
anywhere in the production path. The word "confidence" appears only for
technique candidates (#7) and mock-preview badges.

## 2. Formulas and thresholds

Decision: `is_anomaly = anomaly_score >= threshold`. Bands per §1 row 4.
`risk_score == anomaly_score` exactly (both `round(score, 6)`; live-tested).
Critical/high bands sit above both frozen thresholds, so they always imply
`is_anomaly == true`; medium implies it; low/info imply false. Severity is
computed **solely** from score + threshold — independent of RAG,
provenance, remediation, or family by construction.

## 3. Supported interpretations

- Scores rank anomalousness; thresholds convert rank to review decisions.
- Severity bands communicate magnitude + decision in one ordinal; the
  calibration note forbids reading them as validated risk.
- Technique confidence qualifies candidate relevance, nothing more.
- Session aggregates describe local usage, not model quality.

## 4. Unsupported or ambiguous claims found

1. **`risk_score` naming** (`schemas/detection.py`, API + PDF "Risk Score"):
   contains zero risk modeling — confirmed identical to anomaly score.
   Mitigated in-phase by schema descriptions stating placeholder echo and
   non-probability semantics (OpenAPI-text-only change, contract intact).
   PDF label unchanged (renderer change deferred; disclaimers + note carry
   the meaning).
2. **Mixed severity semantics** (`severity_service.py`): absolute bands
   (magnitude) + relative bands (decision) under one label, with no impact,
   confidence, or family-blindness dimension. P1-8 makes this material:
   OP-A PortScan recall is 0.008, so a "critical" PortScan-pattern score
   overstates actionable meaning — severity cannot see family blindness.
   Documented here; bands frozen per scope.
3. **Mock-preview "High likelihood of malicious activity"**
   (`detections/[id]/page.tsx:179`, mock branch only, SAMPLE-badged) and
   landing-page "Risk-based severity" (`how-it-works.tsx:54-58`) use
   likelihood/risk language for placeholder heuristics. Recorded, not
   changed: mock-only/sample-labeled, and "no broad frontend redesigns"
   applies. Revisit if mock content ever ships unlabeled.
4. **Gauge 0–1 dial** (`charts.tsx:84-101`): clamps the score into a
   probability-looking dial labeled "Anomaly Score". Empirically scores
   stay <0.69, but no bound is proven; clamping could hide extremes.
   Recorded as design observation.
5. **Backend PDF "Anomaly detection is probabilistic"** (disclaimer): intent
   is honest (paired with "candidate for review, not proof"), but strictly
   the scores are not probabilities. Minor; "statistical" would be more
   precise. Recorded, renderer untouched.

## 5. Per-family interpretation limits (from P1-8 evidence)

Severity/confidence must be read against family blindness: web/Infiltration
need OP-B for recall; PortScan largely invisible at OP-A; DDoS-day benign
FPR reaches 0.42; ROC-AUC misleads under imbalance (Thu-Afternoon 0.93 vs
PR-AUC 0.003). A "high" severity on a PortScan-like flow carries the same
band as on a flooding flow with very different detection support. Missing
RAG/provenance/remediation never invalidates the score-derived decision
and severity — but technique attribution and action specificity must stay
uncertain, which the pipeline already enforces via candidate framing.

## 6. Safe wording recommendations

- Keep: "candidate for review, not proof of malicious activity",
  "retrieved-not-confirmed", calibration note everywhere severity appears.
- Prefer "anomaly magnitude band (placeholder)" over "risk" in future copy;
  never "% confidence", "probability of compromise/attack", or "confirmed".
- Mock/preview surfaces must keep SAMPLE labeling (verified present).

## 7. Calibration prerequisites (for DI-007)

Labeled per-explanation correctness data disjoint from training/selection;
proper scoring rules; family-stratified measurement; decision unit fixed at
the explanation/incident level; independent validation before any claim.
Pooled precision 0.63 with family precision 0.001–0.78 proves scores are
not probabilities today. No calibration model fitted in this phase.

## 8. Follow-up priorities

1. PDF "Risk Score" label clarification (renderer + snapshot tests) — small.
2. Mock-preview likelihood wording + Gauge bound documentation — small.
3. Family-aware severity research (not implementation) — medium.
4. Full calibration study per §7 — large, needs new labeled data.
