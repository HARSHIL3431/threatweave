# RAG Intent–Relevance Evaluation Protocol (DI-017, P1-19)

**Evaluation-design phase only.** No benchmark label, review record,
baseline, retrieval behavior, threshold, guard, detector, contract, or
dependency is changed here, and no new authoritative label is created.
All examples are **synthetic illustrations**, never real incident evidence.

## 1. Purpose, scope, non-goals

Retrieval relevance, malicious intent, incident attribution, and remediation
applicability are four independent judgments. Conflating them is the
failure this protocol prevents: a relevant technique does not prove
malicious intent (RB-016 pattern), and neither relevance nor intent proves
actor attribution. This document defines how each dimension is annotated,
adjudicated, measured, and reported — separately — once human-reviewed
scenarios exist (DI-001 prerequisite; 42/42 records still pending).

Non-goals: selecting thresholds (DI-012), hardening guards (DI-010),
grounding advice (DI-006), adjudicating any scenario, or changing any
existing metric's semantics.

## 2. Dimension definitions and decision rules

### A. Retrieval relevance (per retrieved technique × scenario)

- `relevant` — the technique describes the behavior in the scenario.
- `related-too-broad` — related but insufficiently specific (e.g. a parent
  where only the sub-technique's mechanism is described, or vice versa
  where specificity matters to the question asked).
- `plausible-alternative` — a defensible rival reading (RB-014's T1685.005
  vs T1070 is the reference dispute: both behaviorally supported, exactly
  one currently credited).
- `irrelevant` — no behavioral support.
- `insufficient-evidence` — the scenario text is too thin to judge.

Parent/sub-technique rule (reuses the benchmark convention, unchanged):
a retrieved sub-technique satisfies an expected parent; a retrieved parent
does **not** satisfy an expected sub-technique. Competing explanations are
recorded per-technique, never averaged: multi-label scenarios keep every
defensible ID with its own relevance verdict. Existing P/R/MRR semantics
are untouched — this dimension only supplies adjudicated relevance sets
to feed them. Any incompatibility found during adjudication is documented,
never silently absorbed into metric code.

### B. Intent evidence (per scenario, never per technique)

- `supported-malicious` — scenario states explicitly hostile behavior
  (e.g. SYNTHETIC: "the intruder deletes logs to erase evidence").
- `consistent-not-conclusive` — suspicious but explicable otherwise
  (SYNTHETIC: "logins at 3 a.m. from a new device" with no stated purpose).
- `benign-authorized` — scenario supports legitimate activity (SYNTHETIC:
  "scheduled antivirus scan completed, no threats found").
- `ambiguous` — evidence points both ways with no decider.
- `insufficient-evidence` — too little content to assess (SYNTHETIC: "the").

Intent is never inferred from technique presence, suspicious wording,
repeated failures, retrieval scores, or anomaly scores alone. A scenario
may be `relevant`-retrieving yet `benign-authorized` (the RB-016 shape);
that combination is a first-class, expected outcome — not a contradiction.

### C. Attribution (per scenario)

- `supported` — evidence names the actor/malware/root cause with
  corroboration inside the scenario.
- `candidate-uncertain` — a named hypothesis framed as hypothesis.
- `unsupported` — a specific attribution with no scenario support.
- `not-applicable` — nothing to attribute (and that is fine: missing
  attribution is **not** a model failure when evidence is silent).

### D. Remediation applicability (per recommended action × scenario)

- `directly-applicable` — matches observed behavior and evidence.
- `verify-first` — potentially applicable but needs a stated check.
- `overly-broad` — disproportionate to evidence strength (mass resets,
  broad blocks, wipes on a single-flow candidate).
- `unsupported` — no evidence link (invented entities, contradicted
  mitigations).
- `not-assessable` — evidence too thin to judge.

Destructive and broad-impact interventions default to `verify-first` at
best: irreversibility plus weak evidence can never be `directly-applicable`.

## 3. Evidence requirements; insufficient evidence

Every non-`insufficient-evidence` verdict cites the scenario spans and/or
technique definitions supporting it. `insufficient-evidence` is correct
when: the scenario is degenerate or off-domain; the behavior is named
without mechanism ("malicious activity was seen"); or rival readings tie
with no decider. Reviewers must prefer `insufficient-evidence` over
forcing a verdict — it is a measurement outcome with its own rate, not a
failure to decide.

## 4. Reviewer procedure, confidence, disagreement, agreement

- Reviewers annotate all four dimensions independently, blind to retrieval
  ranks/scores and to each other's work; two independent reviewers minimum
  per scenario (exact count is an owner decision).
- Each verdict carries reviewer confidence (`high`/`medium`/`low`) and
  rationale with cited spans. Low-confidence verdicts are data, not defects.
- Disagreements go to adjudication by a third qualified reviewer; forced
  consensus is forbidden — persistent ties stay `insufficient-evidence`
  (relevance) / `ambiguous` (intent) with both positions recorded.
- Agreement is measured per dimension: pairwise percent agreement plus
  Cohen's kappa with confidence intervals, and the adjudication rate
  (fraction requiring the third reviewer). Low agreement on a dimension
  invalidates that dimension's metrics until definitions are repaired —
  it never silently averages away.

## 5. Dev/held-out separation and leakage control

Scenarios split into development and held-out sets on normalized scenario
keys **before** any analysis (same rule as the threshold protocol: v1/v2
share 17 byte-identical payloads under stable case IDs, so version-qualified
record splits leak). `validate_threshold_split`-style disjointness applies
to annotation work equally. All rubric/metric development uses dev only;
held-out is annotated once and evaluated once. With 25 unique scenarios
and 0 adjudicated today, no defensible split exists — collection continues
until the owner-predeclared minimum is met.

## 6. Metrics (separate per dimension; never one fused score)

- **Retrieval:** precision/recall under existing relevance definitions,
  fed by adjudicated relevance sets; existing benchmark P/R/MRR semantics
  unchanged and **never reinterpreted as intent/attribution metrics**.
- **Unsupported-intent-claim rate:** intent claims lacking supporting
  evidence ÷ intent claims made; reported alongside the claim rate and
  abstention rate (scenarios with no claim).
- **Unsupported-attribution-claim rate:** same structure; `not-applicable`
  scenarios excluded from the denominator (never counted as failures).
- **Unsupported/disproportionate-remediation rate:** actions verdict
  `unsupported` or `overly-broad` ÷ actions recommended.
- **Coverage/abstention** per dimension; **agreement + adjudication
  rate** per dimension (§4).
- **Stratification** by adjudicated scenario class (malicious / benign /
  ambiguous / insufficient-evidence): every rate reported per stratum.
- Denominators stated per metric; empty denominators yield `None`, not
  zero; unresolved labels excluded from primary rates with best/worst-case
  sensitivity bounds; uncertainty via Wilson intervals for rates (n always
  reported). **No acceptance thresholds are set here** — all pass/fail
  criteria are owner decisions predeclared before held-out evaluation.

## 7. Reporting and promotion

Per-case results (all four verdicts + confidences + adjudication trail),
aggregate rates with intervals, stratum tables, unresolved counts with
bounds, and agreement statistics. Promotion of any downstream use (policy,
threshold, guard change, contract wording) requires explicit owner
approval against predeclared criteria; otherwise the outcome is recorded
as "insufficient evidence" and work continues.

## 8. Relations to DI-010, DI-006, DI-012

- **DI-010:** guards enforce *phrasing* (candidate framing, no unqualified
  confirmation); they cannot verify whether an intent/attribution claim
  is *true*. This protocol's claim-rate metrics are the measurement
  complement guards cannot supply lexically.
- **DI-006:** the rubric's evidence-alignment and proportionality map to
  dimension D; a lexically qualified action ("consider wiping…") can still
  be `overly-broad` or `unsupported` here — qualification ≠ applicability.
- **DI-012:** a retrieval threshold gates *relevance scores* and shapes
  no-match behavior (technique-described vs not). **Threshold passage
  establishes neither malicious intent nor attribution**, and no-match
  means "no technique described", not "benign". Any future threshold
  documentation must carry these limits.

## 9. Future schema (proposed, NOT implemented)

A future owner-approved change (e.g. `rag-benchmark-v3` or an annotation
sidecar) may add per-scenario fields — adjudicated relevance set, intent,
attribution, remediation-applicability verdicts, reviewer provenance —
with evaluator support that leaves current P/R/MRR semantics byte-identical
for existing cases. Proposed here; implementation requires owner approval
and follows DI-001 adjudication, never precedes it.

## 10. Known limitations

Synthetic scenarios cannot validate real-incident judgment; 25 scenarios
cannot support firm rates (intervals will show it); agreement shortfalls
invalidate dimensions rather than resolve them; and "insufficient
evidence" is the correct, reportable result whenever evidence, agreement,
or data volume falls short.
