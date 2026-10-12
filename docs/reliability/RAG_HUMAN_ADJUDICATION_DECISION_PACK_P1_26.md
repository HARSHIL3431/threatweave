# RAG Human Adjudication Decision Pack (P1-26, DI-001)

Owner-ready packet. **Nothing here is a human decision**: all 42 review
records remain `pending`, all labels synthetic, all baselines untouched.
Exact queries, labels, retrieval, and proposals below are transcribed from
current artifacts (verified 2026-10-12; fixture hashes in §1).

## 1. Reconciled inventory (verified, zero inconsistencies found)

- v1: 17 records (15 match + 2 no-match). v2: 25 records (16 match +
  9 no-match). Shared scenarios: 17, payloads byte-identical.
  v2-only: RB-016, RB-017, RB-N03–N08. Unique scenarios: 25.
- Review queue: 42 version-specific records, **42 pending / 0 decided**,
  reviewer blocks all blank. Queue `original` blocks match fixtures
  exactly; baseline case order matches benchmarks exactly.
- Automated proposals (all **UNAPPROVED**, analyzer
  `automated-analysis`): 39× `accept` (36 high, 3 medium), 2×
  `needs-domain-review` (RB-014 both versions, medium), 1× `accept` with
  caveat (RB-016, medium). `proposed_change`: RB-014 label suggestion
  (both versions), RB-016 schema suggestion (v2 only).
- Fixture sha256 (prefix): v1 `9314852a36a3`, v2 `7a77a797cffd`, queue
  `8c10fc81cbbf`, baseline v1 `d131aaf60e07`, v2 `1d65e33b84c3`.
- **Version sharing rule:** the 17 shared scenarios carry identical
  payloads, so one scenario judgment applies to both version records
  (recorded twice with shared rationale). RB-016/RB-017/RB-N03–N08 are
  v2-only and decided once.

## 2. Priority decision tables

Dimensions per the DI-017 protocol (relevance / intent / attribution /
remediation-applicability, judged independently). Retrieval ranks/scores
are context for score-behavior questions only — never evidence for a
label. Blank `Decision: ___` fields await the authorized reviewer
(identity + date + rationale required by the queue validator).

### RB-014 — taxonomy dispute (v1 + v2 records) — needs ATT&CK expertise

- Query: "An intruder deletes system event logs to erase evidence of their activity." Expected: [T1070].
- Retrieved: T1685.005 (0.6774), T1685.006, T1685.001, T1685.004, T1070.004 (0.5464). RR 0.2.
- Evidence on file: T1070 = selectively delete/modify artifacts to reduce
  presence indications (Stealth); T1685.005 = clear Windows Event Logs to
  hide intrusion activity via wevtutil/Event Viewer/PowerShell/direct
  deletion (Defense Impairment). Full quotes: evidence review §2.
- Question: single-label T1070 vs multi-label including the T1685
  family; does Stealth-vs-Defense-Impairment framing matter here; what
  precedent does this set vs distinct-mechanism rivals (RB-002, RB-009)?
- Alternatives: (a) retain T1070-only (current metric R@5=1.0 hinges on
  rank-5 hit); (b) credit T1070+T1685(.005) (precedent: RB-001/006/009
  multi-labels). Either is defensible; the choice changes baseline
  interpretation, not retrieval.
- Unapproved suggestion: consider T1685-family credit — DO NOT apply
  without sign-off. Decision: ___

### RB-016 — gray zone (v2 only)

- Query: "A user cannot log in after a password reset and the helpdesk says the account appears locked." Expected: [T1110].
- Retrieved: T1531 (0.4471), T1201, T1556, T1110.001 (0.3638), T1110 (0.3542). RR 0.25.
- Framing: relevance probe ONLY — most real instances are benign
  lockouts; T1110's definition covers guessing-based attempts, which a
  post-reset lockout does not involve. Relevant hits score BELOW benign
  RB-017's 0.4341.
- Question: ratify relevance-without-malice; is T1110 fit for purpose;
  is the future `intent` annotation (DI-017) required?
- Intent: benign-authorized (likely) vs ambiguous — reviewer judges from
  query text alone. Attribution: not-applicable. Decision: ___

### RB-017 — no-match under lexical attraction (v2 only)

- Query: "Scheduled antivirus scan completed overnight with no threats found on any workstation." Expected: no-match.
- Retrieved: T1685 (0.4341, highest no-match score either version),
  T1685.005, T1679, T1564.012, T1027.005.
- Question: confirm no technique is described and the 0.4341 is lexical
  attraction (security vocabulary), not a label defect. A no-match here
  asserts nothing about the corpus lacking related content. Decision: ___

### Total misses — retrieval failure or label overbreadth? (v1 + v2 records each)

| Case | Query (exact) | Expected | Top retrieved | Question |
|---|---|---|---|---|
| RB-001 | "An adversary probes the network with ping sweeps and port scans to find live hosts before attacking." | T1595, T1046 | T1016.001 (0.6485), RR 0.0 | Confirm dual-label from definitions; miss = retrieval failure? |
| RB-002 | "Malware lists the services running on remote Windows hosts to identify vulnerable targets." | T1046 | T1569.002 (0.5728), RR 0.0 | Confirm T1046 vs officially-distinct T1569.002 (execute vs list). |
| RB-010 | "Stolen documents are smuggled out hidden inside ordinary command-and-control web traffic." | T1041 | T1027.006 (0.5382), RR 0.0 | Confirm T1041 scope; adjacent misses are not counter-evidence? |
| RB-012 | "Malware searches the local file system and application configuration files for sensitive documents." | T1005 | T1608.001 (0.5648), RR 0.0 | Confirm near-verbatim T1005; misses are stage-adjacent? |
| RB-015 | "An attacker fingerprints which TCP ports are open on the company mail server." | T1046 | T1071.003 (0.5762), RR 0.0 | Confirm T1046; intentional RB-001/002 overlap OK? |

Intent for all five: explicitly supported malicious (hostile language in
query). Attribution: not-applicable throughout (no actor named).
Decision per case: ___

### Near-neighbor rivals — scope boundaries (v1 + v2 records each)

- **RB-005** "An attacker tries thousands of common passwords against the corporate VPN login page." → [T1110]; rival T1056.003 rank 1 (0.524) vs T1110 (0.5104). Question: T1110-only scope with T1056.003 as scenario-neighbor (portal-code theft vs guessing)? Decision: ___
- **RB-009** "An adversary logs in over SSH with stolen credentials and copies hacking tools onto the newly accessed server." → [T1021, T1570]; rival T1563.001 top (0.673) vs T1021 rank 3. Question: confirm new-session login vs session-hijack distinction and dual-label. Decision: ___
- **RB-002** rival T1569.002: see row above (lexical "service" trap).
- **RB-006** "Malware creates a scheduled task so its payload runs every time a user logs on." → [T1053, T1547]; T1053 rank 1 (0.5983), T1547 absent top-5, neighbors T1543.001/T1546 retrieved. Question: dual-label acceptability. Decision: ___

### Borderline / degenerate no-match (v2 only)

- **RB-N06** "Restart the Jenkins build agent on the Windows build server after patching." → no-match (max 0.1859, lowest benign). Question: confirmed no-match (routine admin) vs insufficient-evidence (borderline operational wording)? Decision: ___
- **RB-N08** "the" → no-match (max 0.1781). Question: confirm degenerate-input framing (behavior probe, not correctness). Decision: ___

### Remaining 10 scenarios (routine confirmations)

RB-003/004/007/008/011/013 (rank-1 or policy-credited, directly
supported), RB-N01–N05/N07 (plain no-match). Reviewer confirms from
definitions; live-page re-verification of Tier-2-only IDs is future work,
not a blocker. Decisions: ___ (per record)

## 3. Adjudication workflow (minimal)

1. Owner names the authorized reviewer(s) + required expertise
   (ATT&CK-qualified sign-off required for RB-014 and cross-tactic revises).
2. Reviewer works priority order (§2), blind to ranks first, four
   dimensions independently.
3. Each decision enters the queue per the adjudication guide (§5–6):
   identity/date/decision/rationale, `pending`→`decided`, shared scenarios
   recorded in both version records. Automated proposals stay untouched.
4. Ambiguous/disputed cases stay `needs-domain-review` with positions +
   missing evidence named; independent second review before any
   reconciliation; no forced consensus.
5. Owner signs off the decided queue (sign-off identity recorded with the
   commit). Versioned update ships later: new benchmark version (e.g. v3
   or v1.1/v2.1) + migrated queue; v1/v2 fixtures and both baselines
   remain byte-identical forever. New baselines are new files; the P1-14
   gate keeps guarding v1/v2; held-out evaluation precedes any threshold
   discussion (DI-002/DI-012).

## 4. Owner decisions still required (nothing invented here)

Reviewer count and mix; agreement threshold (if any); minimum held-out
size; acceptance targets; `intent`-annotation schema approval (DI-017);
RB-014 taxonomy verdict; production sign-off process. No reviewer count,
threshold, sample size, target, or sign-off is set in this document.

## 5. Next actions after human review

Decided queue → owner sign-off → versioned benchmark + migrated queue →
fresh baselines as NEW files → DI-003 gate on retrieval changes →
DI-002/DI-012 policy work on validated labels → DI-017 annotations
alongside. v1/v2 references never rewritten.

## 6. Limitations and unresolved cases

All Tier-2-only expected IDs await live-page re-verification; local
corpus release mapping unknown (DI-004); 25 scenarios cannot support
firm rates; RB-014/RB-016 outcomes genuinely uncertain until reviewed;
"insufficient evidence" remains a valid, reportable verdict.
