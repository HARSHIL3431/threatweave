# LLM Guard Evaluation Protocol (P1-20, DI-010 + DI-006)

Measurement infrastructure, not a policy change. No guard, threshold,
retrieval, detector, label, baseline, contract, or dependency is modified
here, and no acceptance threshold is set.

## 1. Evaluation unit

One case = one versioned input/output pair: stable case ID (`HI-01`,
`CF-09`, …), category, severity, qualified flag, feature tags (negation,
quotation, multiline, mixed, marker/exemption gaming), full provider-output
JSON (or verbatim `raw` for malformed inputs), allowed IDs/mitigations,
predefined lexical expectation, curated semantic assessment, and review
metadata. Five labels stay separate per case: lexical-guard behavior,
factual grounding, intent claims, attribution claims, remediation
applicability/proportionality. No single pass/fail hides cross-dimension
disagreement. Lexically testable cases (`assessable`) are distinguished
from policy-unclear ones (`unassessable`: UN-01/UN-02), which are counted
apart and excluded from confusion metrics.

## 2. Harness

- Fixture: `backend/tests/fixtures/llm_guard_eval_v1.json` (57 synthetic
  cases; v1, sha-pinned in each report). Reports: `reports/llm_guard_eval/`.
- Logic: `backend/app/services/guard_evaluation.py` (pure: fixture
  validation with clear `GuardEvalError`, per-case runs through the
  **unchanged** `validate_llm_output`, confusion math, Wilson intervals,
  stratification). Runner: `scripts/eval_guard_harness.py`
  (`--fixture/--out`; exit 0 on measured runs, 2 on bad fixtures).
- Guarantees: offline (no keys/network); deterministic (re-runs identical
  modulo invocation path); accepted/rejected/errored/unassessable recorded
  separately; malformed fixtures fail loudly; non-validation exceptions
  become `errored`, never successes; no prompts/secrets logged (only case
  IDs, outcomes, validator error keys).
- Coverage: `backend/tests/unit/test_guard_eval_harness.py` (15 tests:
  confusion math, empty denominators → `None`, Wilson bounds,
  unassessable separation, semantic-gap extraction, error mapping,
  determinism, malformed rejection).

## 3. Metrics (positive class = should-reject)

- **Unsafe acceptance (FN):** expected reject, observed accept.
- **Benign rejection (FP):** expected accept, observed reject.
- **Guard rejection rate:** rejected ÷ scored. **Validation error rate:**
  errored ÷ scored. **Unassessable rate:** unassessable ÷ total — each with
  denominators stated; `None` on empty sets.
- **Semantic grounding failure:** accepted outputs whose curated semantic
  is unsafe/unsupported (listed, never fused into lexical rates — a
  lexical accept is not a safety certificate).
- Stratification: category, severity, qualified, plus feature tags;
  per-stratum confusion summaries. Wilson 95% intervals where n supports
  them. Owner acceptance targets: none set (owner-predeclared, future).

## 4. Track A — deterministic synthetic evaluation (executed, v1)

57 cases, 55 scored: TP 35, FN 0, TN 19, FP 1, 0 errored, 2 unassessable,
3 semantic gaps. Unsafe-acceptance rate 0.0 (95% CI [0.0, 0.10]); benign-
rejection rate 0.05 (1/20: CF-09, the known "No … confirmed" limitation —
an honest measured FP, not a hidden regression); rejection rate 0.65.
Semantic gaps (lexically correct accepts, safety-relevant content):
SG-01 (unsupported attribution), SG-02/SG-03 (unsupported claims) — the
quantified lexical/semantic boundary. UN-01/UN-02 excluded as
policy-unclear. Results describe fixture behavior only, never real-model
performance. Full per-case rows in
`reports/llm_guard_eval/guard_eval_report_v1.json` (fixture sha256,
code rev, command, limitations recorded inside).

## 5. Track B — reviewed real-model samples (unexecuted)

Future protocol (requires owner approval + analyst time; no provider
calls made here): approved model/provider + eval version; sampling
strategy with size rationale; prompt/task categories; secure handling and
redaction; independent dual review with the DI-017 adjudication
procedure; disagreement resolution; annotation of unsupported claims and
disproportionate actions using §1's five labels; FP/FN reporting against
the same metric definitions; model/version-change reproducibility notes.
**Track B has not been executed; no real-model sample exists.**

## 6. Remediation safety coverage (rubric-mapped)

Fixture spans: unsupported CVEs/actors/malware/ports/root causes (CV,
SG-01–03); destructive/broad actions (HI-01–13, HI-20/21, SG-05);
evidence-unsupported advice (HI-05–07); generally-relevant-but-inapplicable
mitigations (HI-19 positive vs HI-07 smuggling negative); qualified advice
(HI-14–16); evidence/advice contradiction and marker/exemption gaming
(HI-02–07, HI-20); expert-judgment cases (HI-14–16, ID-06, SG-01–03
semantics). Every row separates lexical verdict from support/
proportionality. String evaluation cannot establish factual truth (§4
gaps are the exhibit).

## 7. Relations

- **DI-010:** this framework is the measurement complement to lexical
  guards — reproducible FP/FN on policy cases, with the CF-09 honest FP
  as the calibration example.
- **DI-006:** rubric categories map 1:1 onto fixture categories and
  semantic assessments; closure still needs Track B.
- **DI-012/DI-017:** relevance-threshold semantics and the four-dimension
  separation are reused unchanged (scenario-level units, leakage rules,
  `None`-on-empty denominators, "insufficient evidence" as a valid outcome).
