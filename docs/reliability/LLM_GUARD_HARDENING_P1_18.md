# LLM Guard Hardening P1-18 (DI-010 + DI-006)

Implementation phase for the confirmed lexical bypasses in
`LLM_GUARD_AND_REMEDIATION_GAP_AUDIT.md` (G-01–G-06, G-08). G-07 and all
semantic-grounding limits are explicitly **not** claimed fixed. No provider
called; no detector, retrieval, index, label, baseline, threshold, contract,
or dependency changed.

## 1. Root causes and fixes (all in `backend/app/services/llm_validation.py`)

- **G-01 marker gaming → clause-scoped qualification.** Markers were matched
  against the whole action. Now `_split_clauses` (`[.!?;:\n]+`) scopes each
  marker to its clause; the only cross-clause exemption is an explicit
  conditional (`_CONDITIONAL_MARKERS`: if/once/after/pending/subject-to/…)
  in an adjacent clause. Bare hedges ("Review:", "Consider … later") no
  longer exempt separate instructions, while "Isolate the host after
  verifying scope …" and "If the analyst confirms …: isolate the host"
  still pass. Known trade-off: colon-structured advice without an explicit
  conditional in either clause is now strict (documented, accepted).
- **G-02 exemption smuggling → span redaction.** The boolean
  `_is_mitigation_grounded` (any substring exempts everything) is replaced
  by `_redact_grounded_spans`: only the template span through the quoted
  retrieved text, or bare retrieved-mitigation spans, are removed; the
  high-impact check runs on the remainder. Appended destruction is now
  caught; verbatim STIX quotes still pass.
- **G-03 synonyms → six narrow patterns** (at-scale credential reset with
  account/password object required; take-…-offline; suspend; reboot —
  bare `restart` deliberately stays routine; lock-out; deactivate).
  Negated ("do not delete") and double-quoted (`"delete"`) mentions are
  not instructions (`_NEGATION_RE`, `_QUOTED_SPAN_RE`), so prohibitions
  and word-mentions stop failing.
- **G-04 hedge injection → positional hedge.** `_confirmatory_term_unhedged`
  counts only markers *preceding* the term. "… is confirmed, possible
  false positive?" now fails; "not confirmed" / "possible attack …"
  still pass.
- **G-05 CVE variants → broadened separator class** (ASCII + unicode
  dashes, whitespace, underscore; both numeric groups still required, so
  "CVE database" prose is unaffected). No external lookup; string shape
  only, never a reality claim.
- **G-06 ID obfuscation → `_normalize_technique_ids`** folds "T 9999" /
  "T-9999" to canonical form before the smuggle scan. Exact-ID semantics
  preserved: un-supplied sub-techniques (T1046.001 when only T1046 was
  retrieved) are still rejected.
- **G-08 newlines → `_squash_ws`** collapses whitespace before
  confirmatory matching ("proof\nof" now fails); clause splitting treats
  newlines as boundaries without concatenating tokens.

Caller contract unchanged: same `validate_llm_output(raw, allowed_ids,
allowed_mitigations)` signature, same exception type, same error keys and
detail shapes (`unqualified_high_impact_action: [{index, trigger≤40}]`).
Both callers (`llm_service.generate_explanation`, `reports.py` report
validation) required no changes.

## 2. Before/after on every reproduced P1-17 bypass

| Bypass input | Before (P1-17) | After |
|---|---|---|
| `Wipe the server. Consider implications later.` | accepted | **rejected** (`unqualified_high_impact_action`) |
| `Review: delete all logs now.` | accepted | **rejected** |
| `Possible side effects include downtime; delete all logs now.` | accepted | **rejected** |
| `Delete all system logs. Monitor network traffic for unusual activity` | accepted (exempt) | **rejected** |
| `Mitigation (per T1046): Delete everything now.` | accepted (exempt) | **rejected** |
| `Mitigation (per T1046): Disable unused services. Also delete all logs.` | accepted (exempt) | **rejected** |
| Reset-at-scale / take-offline / suspend / reboot / lock-out / deactivate (unqualified) | accepted | **rejected** |
| `The intrusion is confirmed, possible false positive?` | accepted | **rejected** (`confirmatory_language`) |
| `CVE 2024 1234`, en/em-dash CVE shapes | accepted | **rejected** (`unsupported_factual_claim`) |
| `T 9999`, `T-9999` in prose | accepted | **rejected** (`ungrounded_technique_mentions`) |
| `proof\nof`, `without\na doubt`, `attributed\nto` | accepted | **rejected** |
| `Consider isolating the host if follow-up confirms …` | accepted | accepted (unchanged) |
| `Mitigation (per T1046): Disable unused services.` (+ retrieved) | accepted | accepted (unchanged) |
| `The attack is confirmed?` / `No doubt this is confirmed.` | rejected | rejected (unchanged) |

Five new-test expectations written during this phase initially failed and
were corrected after analysis proved the implementation right and the
expectation wrong (wrong mitigation list supplied; "confirmed"-bearing
positive; "No … confirmed" and sub-technique prose — both rejected before
and after, i.e. pre-existing strictness, not regressions). No pre-existing
test required any change: the full pre-phase suite passes unmodified.

## 3. Positive controls and false positives observed

- 20+ positive controls pass: qualified/unqualified-routine advice,
  negations, quotations, mixed safe/unsafe (flagged at the right index),
  generic vulnerability prose, canonical ID references, mock-provider
  outputs end to end.
- Remaining known false Strictness (documented, not silently fixed):
  "No attack has been confirmed by the available evidence" is rejected
  ("no" is not a hedge marker — adding it would exempt "No doubt this is
  confirmed", so the trade-off was kept); "unconfirmed" as a single word
  is rejected (pre-existing); single-password "reset the admin password"
  passes unqualified (routine-ops line, by design); restart ≠ reboot by
  design.

## 4. Bypasses that remain (not claimed fixed)

G-07 invented entities (no lexical fix exists); L-01 exemption breadth vs
shortest retrieved mitigation; L-02 abbreviation sentence-splitting;
L-04 real-model frequency; H-01/H-02 semantic truth and proportionality.
Five-digit shapes ("T10465") are not valid ATT&CK IDs and stay out of
scope. Lexical validation bounds phrasing; it does not establish that
advice is true, wise, or proportionate.

## 5. Measuring FP/FN next (recommendation)

Collect governed real-model outputs (opt-in runs) into a labeled prose
set; report per-guard precision/recall with the severity-weighted cost
model (false suppression of safe advice vs escaped destructive advice);
tighten patterns only with those numbers (DI-010 acceptance). The
deterministic fixtures plus the 126-test guard suite are the regression
floor, not the measurement.

## 6. Tests

Extended `backend/tests/unit/test_llm_guard_boundaries.py` (was 11, now
~60 tests): every P1-17 bypass as a rejection test, positive controls for
legitimate advice, negation/quotation/multiline/mixed cases, malformed and
non-string inputs. Existing grounding, remediation, and service suites
unchanged and green.
