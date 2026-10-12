# Remediation-Grounding Rubric (P1-9)

Reviewable standard for `recommended_actions` in validated explanations.
Enforced only where deterministic checks are reliable; everything else is
explicitly marked as requiring human judgment. Status: rubric v1, synthetic
fixtures, no expert validation.

## Scope categories

- **Evidence alignment:** the action must respond to behavior actually
  detected (anomaly score vs threshold, severity, flow features such as
  ports/rates/flags) or to a retrieved ATT&CK candidate — never to invented
  hosts, accounts, CVEs, malware families, or root causes. The evidence
  packet contains **no** hostnames, usernames, IP addresses, CVE numbers,
  or malware names, so any specific instance of these in recommendations is
  unsupported by construction.
- **Source support:** an action is *mitigation-grounded* when it quotes or
  attributes retrieved ATT&CK mitigations/detection guidance (authoritative
  STIX content), otherwise it is model-generated advice and must read as
  generic defensive guidance, not incident-specific fact.
- **Scope:** target the affected flow/service/port under review. Do not
  assume a larger incident (no lateral spread, no compromise beyond the
  single scored flow).
- **Proportionality:** match intervention strength to evidence strength
  (P1-8: OP-A misses entire families; a single anomalous flow is a review
  candidate, not a confirmed intrusion).
- **Operational safety:** disabling accounts, isolating hosts, broad blocks,
  log deletion, wipes, and service termination are high-impact: they need
  explicit qualification (conditional language + verification step) unless
  they quote retrieved mitigations.
- **Uncertainty disclosure:** hypotheses must read as hypotheses; absence of
  RAG context must be admitted (enforced by `_ensure_context_limitation`).
- **ATT&CK integrity:** technique IDs/names already enforced (P1-3); reasons
  must stay candidate-framed.
- **Verification and rollback:** prefer actions naming a check ("review
  logs", "corroborate indicators", "monitor") over irreversible steps.

## Deterministically enforced rules (in `llm_validation.py`)

1. `unqualified_high_impact_action`: a non-mitigation-grounded action
   matching a high-impact verb pattern (isolat*, quarantin*, disabl*,
   shutdown, wipe, reimage, delet*, terminat*, revok*, block, disconnect,
   …) with no qualification marker (consider, if/after/once/pending,
   review, verify, corroborate, candidate/potential/possible, may/might/
   could, …) fails validation.
2. `unsupported_factual_claim`: a `CVE-YYYY-NNNN` mention anywhere in free
   text fails — no CVE data exists anywhere in the pipeline.
3. Pre-existing: smuggled-ID scan and confirmatory-language guard also scan
   `recommended_actions`.

## Explicitly NOT enforced (human judgment required)

Invented hostnames/accounts/root causes without high-impact verbs or CVE
patterns; malware-family or threat-actor attribution by name; invented
port/service facts; proportionality judgments; whether a qualified action
is wise (only that it is qualified). Claiming otherwise would pretend
string matching proves semantic correctness.
