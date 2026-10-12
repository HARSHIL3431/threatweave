# RAG Threshold Derivation Protocol (DI-012, P1-16)

**Status: procedure only. No production threshold exists, none is proposed,
and none is validated here.** Production retrieval returns top-K
unconditionally and must remain unchanged until every condition in §8 is
satisfied. All worked numbers in this document are already-recorded
synthetic observations — never threshold recommendations.

## 1. Verified score semantics (read from current code, 2026-10-12)

- **Similarity, not probability.** Query and corpus vectors are both
  L2-normalized (`EmbeddingService.embed` with `normalize_embeddings=True`,
  float32 — `backend/app/services/embedding_service.py:38-53`; the index
  builder embeds corpus text through the same method —
  `scripts/build_mitre_index.py:143-145`). The index is FAISS `IndexFlatIP`
  over those normalized vectors (`vector_store.py:153`), so each score is an
  **inner product equal to cosine similarity** up to float32 arithmetic
  error. Observed range on this corpus is roughly [0.1, 0.75]; nothing
  bounds scores to a calibrated scale.
- **Representation and precision.** `VectorStore.search` stores
  `round(float(score), 6)` per hit and sorts descending
  (`vector_store.py:87-96`). Threshold comparisons use **`score >= floor`
  on these stored 6-decimal scores** — the same convention as the offline
  `apply_score_floor` helper (`rag_evaluation.py`). Never compare
  re-rounded display text: `format_retrieval_result` prints 4 decimals and
  saved baselines record `round(s, 4)`; a score within ~5e-7 of a candidate
  floor is rounding-sensitive, so the pinned comparison precision (6
  decimals, `>=`) is part of every experiment's metadata (§7).
- **Top-K is unconditional.** Retrieval returns `min(top_k, ntotal)` hits
  with no floor, margin, or no-match verdict in the production path
  (`rag_service.py:210`, `vector_store.py:73`). The offline policy helpers
  (`apply_score_floor`, `apply_score_margin`, `evaluate_policy`) are
  evaluation tooling only and are not wired into production.
- **Empty, failure, and integrity representations.**
  - Healthy-but-empty: `[]` (empty index, or every hit position invalid).
    The query path records `RAG_RETRIEVAL_EMPTY` and returns the empty list;
    the detection-integration shims (`retrieve_context`,
    `retrieve_evidence`) likewise return `[]` and never raise.
  - Empty/blank query: `ValueError` (invalid input, not a retrieval result).
  - Index missing or integrity failure: fail-closed unavailable
    (`RagUnavailableException` → 503 `RAG_UNAVAILABLE`); integrity defects
    raise `VectorStoreIntegrityError`, never a degraded index.
  - Embedding or search exceptions propagate to the caller and are counted
    by observability categories — they are errors, not low scores.
- **Relevance ≠ malice.** A score measures text similarity between a query
  and technique descriptions. It carries no information about whether the
  described event is malicious: the benchmark's own gray-zone case (RB-016,
  a likely-benign lockout retrieving T1110) exists to prove the point.
  **A score threshold can therefore only ever gate retrieval relevance —
  it cannot independently establish that an event is malicious,** and any
  future threshold must ship with that limitation documented, not with
  malice-implying language.

## 2. Required labels and review (A)

Threshold work may only begin on **human-adjudicated relevance labels**
(DI-001 output): each scenario labeled `relevant` (confirmed technique(s)
described, with IDs), `no_match` (confirmed none described), or
`unresolved` (ambiguous, insufficient evidence, or reviewer disagreement).

- Unresolved scenarios are **excluded from primary threshold selection**;
  their count is reported and their recorded max scores feed a sensitivity
  analysis: recompute retention/suppression bounds treating unresolved as
  relevant (retention lower bound) and as no-match (suppression lower
  bound), and report both. If the bounds admit no defensible floor, the
  outcome is "insufficient evidence" (§5).
- Relevance assessment and malicious-intent assessment stay separate
  throughout (DI-017 dimension gap). A scenario can be relevant-but-benign;
  intent labels, when they exist, are never threshold inputs.

## 3. Evaluation unit and data separation (B)

- The classified unit is **one retrieval query/scenario** (one benchmark
  case). Detector flows or incidents are not the unit unless a separate,
  validated aggregation method is explicitly specified and reviewed.
- Split scenarios into **development (selection) and held-out (evaluation)
  sets before any threshold is compared**, on normalized scenario keys —
  never on version-qualified records: v1/v2 share 17 byte-identical
  payloads under stable case IDs, so a per-record split leaks scenarios
  across the boundary. `validate_threshold_split` enforces non-empty,
  duplicate-free, disjoint scenario sets and rejects any overlap as a leak.
- The same scenarios must never select and evaluate a threshold (no
  choose-and-report on one sample). Threshold selection runs on dev only;
  the chosen candidate is evaluated once on held-out cases with
  uncertainty reporting (§5).
- If the adjudicated set is too small for a defensible split, the protocol
  says so and defers: **with 25 unique scenarios and 0 adjudicated today,
  no split is defensible and selection cannot proceed.** The owner
  predeclares the minimum held-out size; until it is met, every run ends in
  "insufficient evidence".

## 4. Metrics and trade-offs (C)

Measured per candidate floor with `evaluate_candidate_threshold`
(adjudicated labels in, rates out):

- **Relevant-match retention** (recall): relevant scenarios keeping ≥1
  relevant hit at/above the floor. Denominator: scored relevant scenarios.
- **False suppression**: relevant scenarios with zero relevant hits
  at/above the floor (the costliest error class). Same denominator.
- **No-match suppression**: no-match scenarios with every score below the
  floor. Denominator: scored no-match scenarios.
- **Unresolved counts + sensitivity bounds** (§2), **coverage and
  retrieval errors** (missing recordings and invalid scores are errors:
  counted, excluded from denominators, never silently dropped).
- Per-case rows (max score, max relevant score, outcome) and aggregates;
  rates are `None` — not zero — when a denominator is empty.

Denominator and empty-set rules are fixed: an **empty result set retains
nothing** (a relevant scenario with `[]` is suppressed) and **suppresses
vacuously** (a no-match scenario with `[]` is suppressed). Every metric
states its denominator; every report lists errors.

Score distributions must be inspected, not assumed: the already-recorded
synthetic observations show **overlapping classes, not clean separation**
— retrieval misses reach 0.648–0.677 (RB-001/009/014 rival hits) while the
top benign no-match score is 0.4341 (RB-017), and RB-016's relevant T1110
hits (0.3638/0.3542) sit *below* that benign maximum. Any future proposal
built on overlapping distributions must say so and price the overlap
explicitly. (Synthetic, non-authoritative context — not a derivation.)

## 5. Threshold-selection rule (D)

Compare candidate floors under a predeclared, owner-approved rule:

1. Owner approves **acceptable recall and suppression criteria** and a
   written rationale for the relative cost of false suppression versus
   irrelevant retrieval *before* candidates are scored. No targets are set
   in this document and none are implied.
2. Score candidates on **dev scenarios only**; select at most one
   candidate; evaluate it **once on held-out scenarios**.
3. Report confidence intervals (or another appropriate uncertainty
   treatment) on held-out retention and suppression, plus per-case
   regression analysis (which scenarios change outcome vs the no-floor
   baseline, and why each change is acceptable).
4. If criteria are unmet, bounds overlap unusably, or data are too few,
   the recorded outcome is **"insufficient evidence"** — never a
   best-available floor promoted on weak grounds.

## 6. Compatibility and reproducibility (E)

Every threshold experiment pins: benchmark version + content hash,
adjudication version + per-record decision status, corpus/index
fingerprint + provenance (`doc_count`, `technique_count`,
`subtechnique_count`, `embedding_model`, `embedding_dim`,
`bundle_sha256`), embedding model + dimensionality, retrieval config + K
values, score semantics + comparison precision (§1), dev/held-out split +
scenario IDs, the selection rule from §5, code revision, and output
artifact hashes. Reuse the DI-003 comparison gate wherever applicable:
never bypass its fingerprint/version/K/case-set compatibility checks, and
never overwrite the committed `rag_baseline_v1/v2.json` references (fresh
runs go to temp files via the gate's path guard).

## 7. Promotion and rollback requirements (F)

A future threshold ships only after **all** of these hold; until then
production retrieval stays exactly as it is:

- Human review and sign-off recorded (DI-001 adjudication complete for
  every scenario in both splits).
- Sufficient reviewed data per the owner-predeclared minimum (§3).
- Independent held-out evaluation meeting the predeclared criteria (§5),
  with uncertainty and per-case regressions documented.
- No unacceptable per-case regressions (each suppression of a confirmed
  relevant scenario individually justified).
- Limitations documented at the point of use (relevance-only gating;
  corpus/model-specificity; §1 malice caveat).
- Explicit approval to change production behavior, with the API-contract
  impact assessed (response shapes unchanged or contract updated +
  tested).
- Reversible deployment: feature-flag or config-gated rollout with a
  rollback plan that restores unconditional top-K retrieval.

## 8. Frozen-system invariants (this phase changes none of these)

Production detector E2 `with_port` (60 features); `-score_samples()`
semantics and the frozen anomaly decision rule; OP-A threshold
`0.5219193851693676`; OP-B threshold `0.4878500998020172`; frozen severity
logic; production RAG retrieval behavior (unconditional top-K, no floor);
the FAISS index and embedding artifacts; benchmark v1/v2 labels, fixtures,
fingerprints, and saved baselines; existing API response shapes and
dependencies.

## 9. Implementation notes (P1-16)

Pure offline helpers in `backend/app/services/rag_evaluation.py`
(no production wiring, no new dependencies):

- `evaluate_candidate_threshold(labeled_cases, retrieved_by_case,
  threshold)` — adjudicated labels in, retention/false-suppression/
  no-match-suppression rates + per-case rows + unresolved sensitivity data
  + counted errors out. Strict input validation (`ThresholdError` on
  ambiguous labels, duplicate cases, non-finite thresholds/scores).
- `validate_threshold_split(dev_ids, heldout_ids)` — disjoint,
  non-empty, duplicate-free scenario sets; overlap raises as leakage.
- Covered by `backend/tests/unit/test_threshold_derivation.py`
  (boundary `>=` at exact floor, empty-set rules, error counting,
  unresolved exclusion, split leakage incl. the v1/v2 shared-scenario
  collision, determinism). Existing `apply_score_floor` /
  `apply_score_margin` / `evaluate_policy` were reused as-is; no redundant
  policy engine was added.
