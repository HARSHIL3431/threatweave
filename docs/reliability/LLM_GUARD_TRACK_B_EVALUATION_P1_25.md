# LLM Guard Track B Evaluation (P1-25, DI-006 + DI-010)

No live model calls occurred in this phase. No Track B samples exist.

## 1. Readiness decision and evidence: BLOCKED

`python scripts/eval_guard_track_b.py readiness` reports BLOCKED:

- Explicit live-run authorization: **absent**. Neither the task nor the
  repository grants it; the repo's own opt-in convention
  (`THREATWEAVE_REAL_LLM_TEST=1`, `test_llm_real_provider.py:25-32`) is
  unset, and the Track B gate (`THREATWEAVE_TRACKB_LIVE=1`) is unset.
- Provider credential (env): **absent**. A `.env` file on this machine
  contains an `LLM_API_KEY` entry (presence only — value never read,
  displayed, copied, or used); per the mission rule it does not
  constitute authorization and was left untouched.
- Approved input manifest: **present and valid**
  (`backend/tests/fixtures/llm_guard_track_b_manifest_v1.json`, 4 inputs
  over synthetic `sample_flows.json` flows, all annotations pending).
- Supported providers: `openai` (OpenAI-compatible) and `mock`
  (`create_provider`, `llm_providers.py:221-228`); generation path
  `LLMService.generate_explanation` → unchanged `validate_llm_output`
  exercises both the confirmatory-language and remediation guards.

No workaround was implemented and none will be: the runner contains no
network code and no provider invocation by design.

## 2. Track separation

- **Track A (executed, P1-20):** 57 synthetic cases, 55 scored (TP 35,
  FN 0, TN 19, FP 1 known), 3 semantic gaps. Describes guard behavior on
  the fixture — never real-model performance.
- **Track B (unexecuted):** zero captured outputs, zero annotations, zero
  confusion counts. The two tracks are never pooled; Track B reports
  start empty and fill only from authorized captures.

## 3. Methodology and rubric

Capture (authorized manual procedure only): existing opt-in test path or
`POST /api/v1/explain` against manifest flows; bounded volume (4 inputs
v1); save each raw provider output string as `<input_id>.json`; record
provider/model identifiers and capture-time retrieval context
(`allowed_ids`/`allowed_mitigations`) in the manifest; redact before
persisting; one run = one outputs directory (repeat runs never mix).
Measure (offline, deterministic): `scripts/eval_guard_track_b.py
measure` scores annotated inputs through the unchanged validator with
shared Track A confusion math; unannotated inputs list as pending, never
scored. Human review is mandatory for semantic verdicts (reviewer
identity + date recorded per annotation); lexical checks prove no
grounding, proportionality, or attribution claim.

## 4. Privacy and secret-handling rules

No keys in fixtures, manifests, reports, logs, or the repo. Captured
files matching credential shapes (`sk-…`, `Bearer …`) are refused before
parsing. Reports persist outcomes + error keys + hashes only — never
prompts, flows, or raw outputs beyond the captured files' approved
location. Provider errors record separately from guard rejections.

## 5. Results, limitations, owner decisions

Results: none (blocked, §1). False-positive/false-negative measurement
on real outputs is limited by sample size once captures exist (Wilson
intervals, same convention as Track A) and by reviewer agreement on
semantic labels. Unblocking requires, in order: (1) explicit owner
authorization for a bounded capture run; (2) funded credential via the
repo's opt-in convention; (3) analyst time for annotation. No acceptance
targets are set; guards are not declared production-safe on lexical
evidence.
