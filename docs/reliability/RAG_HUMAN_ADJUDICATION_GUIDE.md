# RAG Benchmark Human-Adjudication Guide (DI-001, P1-15)

**Status: review-preparation only. No human adjudication has occurred.**
Every label in the RAG benchmarks is synthetic and **not expert-validated**.
The adjudication queue holds **42 records, all `pending`, 0 human decisions
recorded** (verified 2026-10-12; see §3). Nothing in this guide approves,
revises, or rejects any label. Automated proposals quoted here are
**unapproved machine suggestions**, never ground truth.

## 1. Purpose and non-goals

This guide makes real expert review straightforward, auditable, and useful.
A qualified reviewer works through each benchmark case independently of the
current retrieval ranking and records a decision with identity, date,
rationale, and evidence. That recorded adjudication — not this packet —
is what can eventually satisfy DI-001.

Non-goals (explicitly out of scope for this phase):

- No case is marked reviewed; no reviewer identity, qualification,
  timestamp, or decision is invented.
- No expected ATT&CK ID is changed on the basis of the author's
  interpretation in this packet.
- No benchmark fixture, saved baseline, corpus fingerprint, evaluation
  metric, retrieval ranking, filter, score threshold, FAISS index, or
  embedding artifact is modified.
- Official ATT&CK documentation quoted here is **evidence for the reviewer**,
  not a substitute for human adjudication.
- Preparing this packet does not make the benchmark expert-validated.

## 2. Authoritative acceptance criteria

DI-001 acceptance (register `DEFERRED_IMPROVEMENTS.md`, source of truth;
roadmap `CONSOLIDATED_RELIABILITY_ROADMAP.md` concurs — no material
difference was found between the two definitions and this phase):

> Fixture carries reviewer/date provenance; ambiguous cases re-labeled or
> explicitly retained. Closure requires recorded analyst adjudication with
> identity, date, decision, and rationale per case. Audit artifacts and
> validator coverage alone do not close this item.

DI-001 **remains open** after this phase. §10 lists exactly what is still
outstanding. Items DI-003 and DI-011 remain completed; no other DI item is
opened, closed, or renumbered here.

## 3. Deterministic inventory (verified 2026-10-12)

Counts below were verified programmatically against the current files;
do not rely on remembered numbers.

| Population | Count | Detail |
|---|---|---|
| v1 cases (`rag_benchmark_v1.json`) | 17 | 15 technique-match + 2 no-match (RB-N01, RB-N02) |
| v2 cases (`rag_benchmark_v2.json`) | 25 | 16 technique-match + 9 no-match (RB-N01, RB-N02, RB-017, RB-N03–N08) |
| Shared scenarios (identical payloads) | 17 | Query, expected IDs, and no-match flag verified identical across versions |
| v2-only scenarios | 8 | RB-016, RB-017, RB-N03, RB-N04, RB-N05, RB-N06, RB-N07, RB-N08 |
| **Unique scenarios** | **25** | 16 match (incl. gray-zone RB-016) + 9 no-match (incl. RB-017) |
| Review records (`rag_label_review_v1.json`) | 42 | 17 × `rag-benchmark-v1` + 25 × `rag-benchmark-v2`; version-specific records, **not** 42 unique scenarios |
| Records `pending` | 42 | All reviewer blocks blank (`identity/date/decision/rationale` all null) |
| Records `decided` (human-approved/rejected) | **0** | No existing decisions to preserve; nothing was altered |
| Records with automated `proposed_change` | 3 | RB-014 × 2 versions (label suggestion, unapproved) + RB-016 v2 (schema suggestion, unapproved) |

File hashes (sha256, for reproducibility checks):

- `backend/tests/fixtures/rag_benchmark_v1.json`: `9314852a…bd3e5b6`
- `backend/tests/fixtures/rag_benchmark_v2.json`: `7a77a797…e46cf77d`
- `backend/tests/fixtures/rag_label_review_v1.json`: `8c10fc81…9c8819c8`
- `backend/tests/fixtures/rag_baseline_v1.json`: `d131aaf6…a8c16ff6`
- `backend/tests/fixtures/rag_baseline_v2.json`: `1d65e33b…b9624d9b`

(Full hashes in §11. Baseline metrics: v1 P@5 0.253 / R@5 0.600 /
MRR@5 0.536; v2 P@5 0.263 / R@5 0.625 / MRR@5 0.518; coverage 1.0, no
errors, case order matches benchmarks exactly.)

**How to review shared cases:** the 17 shared scenarios carry identical
payloads in both versions, so adjudicate each unique scenario once and
record the same decision in both version-specific queue records with a
shared rationale (noting the duplication), unless version context gives a
reason to differ — it currently does not. Coverage is counted in records
(42), not scenarios (25).

## 4. The four dimensions — do not conflate them

For every case the reviewer scores four independent questions. A single
label must never collapse them:

1. **Retrieval relevance.** Does the query text describe the behavior that
   ATT&CK technique T defines? Judge from the query and the technique
   definition only. The rank or score at which T is (or is not) retrieved
   is **inadmissible**: a rank-1 hit confers no authority and a total miss
   implies no label error (several recorded misses are documented
   retrieval failures, e.g. RB-001, RB-002, RB-010, RB-012, RB-015).
2. **Malicious intent.** Does the query indicate malicious activity, as
   opposed to benign administration, security operations, or insufficient
   context? Relevance without malice is possible (RB-016 is the designed
   test) and must be recorded as such, not forced into a technique verdict.
3. **Evidence support for a technique.** Is there sufficient cited evidence
   (corpus definition and/or authoritative ATT&CK source, Tier-1 preferred)
   to attach a specific technique ID? Distinguish *defensible match* from
   *insufficient evidence*.
4. **No-match verdict.** If no technique is described — or the description
   is too thin to support any ID — the correct result is `no-match`
   (confirmed), or `insufficient evidence` / `ambiguous` left explicitly
   unresolved. Never upgrade a thin query to a technique to avoid a
   no-match, and never read a relevance score as malice evidence.

## 5. Decision protocol

### 5.1 Allowed reviewer decisions (current schema)

The queue schema (`REVIEW_STATUSES`, `REVIEW_DECISIONS` in
`backend/app/services/rag_evaluation.py:validate_review_queue`) supports
exactly these values. No schema change was made in this phase; gaps are
documented in §9.

| Reviewer outcome | Schema `decision` | Meaning |
|---|---|---|
| Confirmed match, with evidence | `accept` on a match case | Expected ID set is correct; cite supporting evidence; state why rivals were rejected |
| Confirmed no-match | `accept` on a `no_match` case | No ATT&CK technique is described (disambiguated by the record's `original.no_match: true`); confirm benign/empty reading |
| Revised or alternative match, with evidence | `revise` | Expected set should change; describe the exact revised set in `proposed_change.detail` (structured fields proposed, §9); cite evidence |
| Case rejected | `reject` | The case itself is unfit for the benchmark (e.g. incoherent, leaking the answer, unfixable); rationale required. Sparing use expected |
| Ambiguous / insufficient evidence | `needs-domain-review` + rationale stating ambiguity | Evidence cannot support exactly one verdict; record what is missing and what would resolve it |
| Needs additional review / escalation | `needs-domain-review` + rationale stating the escalation | Requires an ATT&CK-qualified second reviewer or authorized research pass; name the question and the expertise needed |

`accept` is disambiguated by `original.no_match`, so confirmed-match and
confirmed-no-match remain distinguishable without a schema change.
`needs-domain-review` covers both terminal ambiguity and escalation; the
rationale **must** state which one it is.

### 5.2 What every decided record must contain

Per the validator (which rejects anything less — automation cannot pose
as human review):

- `reviewer.identity`: who decided (name/handle; **qualification/role**
  goes in the rationale until the schema gains a dedicated field, §9).
- `reviewer.date`: when (ISO date).
- `reviewer.decision`: one of the values above.
- `reviewer.rationale`: why — evidence supporting the decision, why each
  plausible competing technique was accepted or rejected (cite technique
  definitions), whether the original expected label is retained, revised,
  or left unresolved, and (for `revise`) the exact replacement set.
- `status`: flip `pending` → `decided` only together with the full
  reviewer block. Pending records must carry **no** human fields.

### 5.3 Conflicts and escalation

- If multiple reviewers are available: review **independently first**,
  then reconcile. Never simulate multiple reviewers with separate AI
  passes.
- Disagreements are recorded, not averaged: each reviewer files their own
  decided record content; irreconcilable cases stay `needs-domain-review`
  with both positions and the missing evidence named.
- Escalation to an ATT&CK-qualified reviewer is required for taxonomy
  questions (RB-014 is the known instance) and for any `revise` that
  credits a different tactic family. Do not force consensus when evidence
  is ambiguous — unresolved cases remain explicitly unresolved.

## 6. How to work through the queue

1. Read this guide, then the per-case worklist (§8) in the suggested
   priority order (§7).
2. For each scenario, open the source benchmark record (file + case ID in
   §8), the audit analysis
   (`docs/reliability/RAG_BENCHMARK_LABEL_AUDIT.md`), and the evidence
   packet (`docs/reliability/RAG_ATTACK_EVIDENCE_REVIEW.md`, live sources
   accessed 2026-10-11).
3. Assess the four dimensions (§4) from query + definitions — **without
   looking at retrieval ranks first**; recorded scores in §8 are context
   for score-behavior questions only.
4. Check the automated proposal quoted in the worklist: it is explicitly
   **UNAPPROVED** and attributed to `automated-analysis`. It may inform
   but never determines the verdict. If the reviewer agrees with it, that
   agreement is a new human decision with its own rationale — not a
   confirmation of authority the proposal never had.
5. Write the decision into `rag_label_review_v1.json` per §5.2 (both
   version records for shared scenarios), keeping every `original.*`,
   `synthetic: true`, and `automated_proposal` field byte-identical.
6. Run `python -m pytest tests/unit/test_label_review.py -q` from
   `backend/` to validate the queue after edits.

Machine-generated suggestions stay separable by construction: they live
in `automated_proposal` (fixed `analyzer: "automated-analysis"`) and
`proposed_change`, while human decisions live only in `reviewer.*` +
`status`. The validator rejects any mixing (a `decided` status with blank
reviewer fields, or human content in a `pending` record).

## 7. Review priority order (priorities, not pre-decisions)

Work in this order so the highest-value questions get expert time first.
Each entry states the question and the evidence required — never the
answer.

1. **RB-014 (both version records) — taxonomy question.** Recorded
   retrieval credits only rank-5 T1070.004 (score 0.5464) while T1685.005
   occupies ranks 1–4 (up to 0.6774). Question: single-label T1070 vs
   multi-label including the T1685 family; does the Stealth
   (T1070) vs Defense-Impairment (T1685) tactical framing matter for this
   benchmark's purpose? Evidence: authoritative T1070 vs T1685.005 scope
   guidance; ATT&CK-qualified reviewer required.
2. **RB-016 (v2 only) — relevance vs malice.** T1110 hits at ranks 4–5
   (0.3638/0.3542, below benign RB-017's 0.4341) for what reads as a
   benign post-reset lockout. Question: ratify the relevance-without-malice
   framing; is the T1110 label fit for purpose as a relevance probe, and is
   a future `intent` annotation (DI-017) needed? Evidence: reviewer judgment
   on intent from the query text alone.
3. **RB-017 (v2 only) — highest-scoring benign case.** No-match AV-scan
   text retrieves T1685 family at 0.4341. Question: confirm no technique is
   described; confirm the score is lexical attraction, not a label defect.
4. **Total-miss match cases — retrieval failures or label problems?**
   RB-001 (RR 0.0, top 0.6485), RB-002 (RR 0.0), RB-010 (RR 0.0),
   RB-012 (RR 0.0), RB-015 (RR 0.0). Question per case: is the expected
   set defensible from definitions (making these retrieval failures), or
   does the miss expose label overbreadth? Evidence: corpus/ATT&CK
   definitions for each expected ID vs the query.
5. **Near-neighbor rival cases.** RB-005 (T1056.003 retrieved rank 1 at
   0.524 over expected T1110), RB-009 (T1563.001 top hit 0.673 over
   expected T1021 at rank 3), RB-002 (T1569.002 lexical "service" trap),
   RB-006 (dual-label acceptability; T1547 absent top-5). Question per
   case: confirm the expected set and the documented mechanism
   distinctions; state whether rivals merit co-credit.
6. **No-match edge cases.** RB-N06 (routine Jenkins restart — borderline
   administrative wording; lowest benign max 0.1859) and RB-N08
   (degenerate single-stopword input). Question: confirmed no-match with
   the stated framing (borderline-admin; worst-case behavior probe), or
   insufficient-evidence? Evidence: reviewer confirmation of the reading.
7. **Routine confirmations.** Remaining match cases (RB-003/004/007/008/
   011/013: rank-1 or policy-credited hits with direct definition support)
   and plain no-match cases (RB-N01–N05, N07). Live-page re-verification
   of the nine Tier-2-only expected IDs is future work, not a blocker.

## 8. Per-case worklist (25 unique scenarios)

Conventions: **Query** and **Expected** are verbatim from the fixtures —
preserved exactly, never silently reworded. **Proposal (UNAPPROVED)** is
the machine suggestion for that record. **Recorded retrieval** is the
saved baseline top-5 for score-behavior context only. **Question** is what
the reviewer must resolve. Reviewer fields are blank by design.

Shared scenarios list both version records; v2-only scenarios list one.

### RB-001 — port/ping sweep (v1 + v2 records)

- Query: "An adversary probes the network with ping sweeps and port scans to find live hosts before attacking."
- Expected: [T1595, T1046], match. Rationale (fixture): active scanning /
  service-discovery overlap. Ambiguity (fixture): multi-label by design.
- Verified refs: Tier-2 corpus text supports both (audit §RB-001).
- Proposal (UNAPPROVED): `accept`, high — dual-label appropriate.
- Recorded retrieval (v2): RR 0.0; top T1016.001/T1205/T1557 at 0.6485.
  Total miss; audit reads it as retrieval failure.
- Rivals/ambiguity: multi-label acceptability itself is the question.
- Question: confirm the dual-label set from definitions; confirm the miss
  is retrieval failure, not label error.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-002 — remote service listing (v1 + v2 records)

- Query: "Malware lists the services running on remote Windows hosts to identify vulnerable targets."
- Expected: [T1046], match. Rationale: canonical Network Service Discovery.
- Verified refs: Tier-2 T1046 definition (near-verbatim); Tier-1 S5 —
  T1569.002 is *"abuse the Windows service control manager to **execute**
  malicious commands or payloads"* (Execution), officially distinct from
  listing-for-discovery (evidence review §3).
- Proposal (UNAPPROVED): `accept`, high — T1569.002 top hit is a
  lexical-overlap trap.
- Recorded retrieval (v2): RR 0.0; top T1569.002 at 0.5728.
- Question: confirm T1046 and the T1569.002 distinction from definitions.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-003 — OS/hardware inventory (v1 + v2 records)

- Query: "An attacker collects operating system version, patch level, and hardware details from a compromised workstation."
- Expected: [T1082], match. Rationale: System Information Discovery.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high — rank-1 hit (max 0.6325).
- Question: routine confirmation from the T1082 definition.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-004 — LSASS hash dump (v1 + v2 records)

- Query: "An adversary dumps password hashes from LSASS process memory to steal credentials."
- Expected: [T1003], match. Rationale: OS Credential Dumping; parent
  label stable across sub-techniques.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high — T1003.001 rank 1 (max 0.7335).
- Question: routine confirmation, incl. parent/sub-technique policy.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-005 — VPN password guessing (v1 + v2 records)

- Query: "An attacker tries thousands of common passwords against the corporate VPN login page."
- Expected: [T1110], match. Ambiguity (fixture): T1078 is a distinct
  outcome (use vs guessing), not counted.
- Verified refs: Tier-2 T1110 definition; Tier-1 S3 — T1056.003 is
  *"install code on externally facing portals, such as a VPN login page,
  to capture and transmit credentials"*, a distinct mechanism in the same
  scenario (evidence review §3).
- Proposal (UNAPPROVED): `accept`, medium — T1056.003 (rank 1, 0.524) is
  a nearby-alternative mechanism, not a defect.
- Recorded retrieval (v2): RR 0.5; T1056.003/T1110/T1110.003/T1110.001.
- Question: confirm T1110-only scope and that the T1056.003 overlap is
  acceptable ambiguity rather than label error.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-006 — scheduled task at logon (v1 + v2 records)

- Query: "Malware creates a scheduled task so its payload runs every time a user logs on."
- Expected: [T1053, T1547], match. Ambiguity (fixture): multi-label by design.
- Verified refs: Tier-2 corpus text supports both (audit).
- Proposal (UNAPPROVED): `accept`, high — T1053 rank 1 (max 0.5983);
  T1547 absent top-5.
- Rivals: T1543.001/T1546 retrieved are persistence-mechanism neighbors.
- Question: confirm dual-label acceptability from definitions.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-007 — PowerShell via interpreter (v1 + v2 records)

- Query: "An attacker runs malicious PowerShell commands through the Windows command interpreter on a victim host."
- Expected: [T1059], match.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high — T1059.001 rank 1 (max 0.6569).
- Question: routine confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-008 — process injection (v1 + v2 records)

- Query: "A threat actor injects malicious code into a legitimate running process to hide from defenses."
- Expected: [T1055], match.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high — rank-1 hit (max 0.6741).
- Question: routine confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-009 — SSH login + tool copy (v1 + v2 records)

- Query: "An adversary logs in over SSH with stolen credentials and copies hacking tools onto the newly accessed server."
- Expected: [T1021, T1570], match. Ambiguity (fixture): T1078 related but
  not counted; either expected ID is a hit.
- Verified refs: Tier-2 corpus supports both; Tier-1 S4 — *"SSH Hijacking
  differs from use of SSH because it hijacks an existing SSH session
  rather than creating a new session using Valid Accounts"*; the query
  describes credential login (new session), officially distinct from the
  top-hit rival (evidence review §3).
- Proposal (UNAPPROVED): `accept`, high — T1021 rank 3 (0.5699) under
  T1563.001 (0.673), which is mechanistically distinct.
- Question: confirm T1021/T1570 scope, the T1563.001 distinction, and
  dual-label acceptability.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-010 — C2-channeled exfiltration (v1 + v2 records)

- Query: "Stolen documents are smuggled out hidden inside ordinary command-and-control web traffic."
- Expected: [T1041], match. Ambiguity (fixture): T1071 related C2 behavior,
  not counted.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high — T1027.006/T1020 misses are
  mechanism-adjacent, not counter-evidence.
- Recorded retrieval (v2): RR 0.0 (max 0.5382).
- Question: confirm T1041 scope; confirm the miss is retrieval failure.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-011 — passive sniffing (v1 + v2 records)

- Query: "An attacker passively sniffs network traffic to capture passwords sent in clear text."
- Expected: [T1040], match.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high — rank-1 hit (max 0.6359).
- Question: routine confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-012 — local filesystem search (v1 + v2 records)

- Query: "Malware searches the local file system and application configuration files for sensitive documents."
- Expected: [T1005], match.
- Verified refs: Tier-2 T1005 corpus language near-verbatim (audit).
- Proposal (UNAPPROVED): `accept`, high — T1608.001/T1204.002 misses
  concern different attack stages despite "file" overlap.
- Recorded retrieval (v2): RR 0.0 (max 0.5648).
- Question: confirm T1005 scope; confirm the miss is retrieval failure.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-013 — keylogger (v1 + v2 records)

- Query: "A keylogger records everything the user types in order to steal login credentials."
- Expected: [T1056], match.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high — T1056.001 rank 1 (max 0.7108).
- Question: routine confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-014 — event-log deletion (v1 + v2 records) — TOP PRIORITY

- Query: "An intruder deletes system event logs to erase evidence of their activity."
- Expected: [T1070], match. Rationale (fixture): Indicator Removal.
  Ambiguity (fixture): "None known" — superseded by the audit finding below.
- Verified refs: Tier-1 S1 — T1070: *"Adversaries may selectively delete
  or modify artifacts generated to reduce indications of their presence
  and blend in with legitimate activity"* (tactic: Stealth; live
  sub-techniques .003–.010). Tier-1 S2 — T1685.005: *"Adversaries may
  clear Windows Event Logs to hide the activity of an intrusion"* via
  `wevtutil`, Event Viewer, PowerShell, or direct deletion under
  `C:\Windows\System32\winevt\logs\`; sub-technique of T1685 (tactic:
  **Defense Impairment**). Full quotes in evidence review §2.
- Proposal (UNAPPROVED): `needs-domain-review`, medium — T1685.005
  (ranks 1–4, up to 0.6774) is arguably an equally-or-more specific
  correct answer the label does not credit; recorded R@5 = 1.0 rests
  solely on rank-5 T1070.004 (0.5464).
- Unapproved suggestion on file: consider crediting the T1685 family if
  taxonomy review supports it. **Do NOT apply without analyst sign-off.**
- Question (ATT&CK-qualified reviewer required): single vs multi-label;
  whether T1685-family answers are acceptable; whether the
  Stealth-vs-Defense-Impairment framing matters for benchmark purpose;
  the precedent line vs distinct-mechanism rivals (RB-002, RB-009).
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-015 — mail-server port fingerprinting (v1 + v2 records)

- Query: "An attacker fingerprints which TCP ports are open on the company mail server."
- Expected: [T1046], match. Ambiguity (fixture): overlaps RB-001/RB-002
  thematically by design.
- Verified refs: Tier-2 corpus definition directly supports (audit).
- Proposal (UNAPPROVED): `accept`, high.
- Recorded retrieval (v2): RR 0.0 (max 0.5762; top T1071.003).
- Question: confirm T1046 scope; confirm the miss is retrieval failure.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-016 — account lockout wording (v2 record only) — GRAY ZONE

- Query: "A user cannot log in after a password reset and the helpdesk says the account appears locked."
- Expected: [T1110], match. Rationale (fixture): wording overlaps
  credential-guessing retrieval space; most real instances are benign
  lockouts. Ambiguity (fixture): deliberate gray zone — **retrieval
  relevance must not be read as malice**.
- Verified refs: T1110 corpus/official pattern is guessing-based access
  attempts; a post-reset lockout involves no guessing (evidence review §3).
- Proposal (UNAPPROVED): `accept`, medium — fit ONLY as a relevance probe
  with the caveat preserved.
- Recorded retrieval (v2): RR 0.25; T1110.001/T1110 at ranks 4–5
  (0.3638/0.3542) under non-relevant top hits (max 0.4471) — relevant
  scores below benign RB-017's 0.4341.
- Unapproved suggestion on file: optional future `intent` annotation
  (malicious|benign|ambiguous|insufficient-context). Schema-only
  suggestion; does not change this label.
- Question: ratify relevance-without-malice framing; is T1110 fit for
  purpose here; is the `intent` annotation needed (DI-017)?
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-017 — benign AV scan (v2 record only) — no-match

- Query: "Scheduled antivirus scan completed overnight with no threats found on any workstation."
- Expected: no-match. Rationale (fixture): benign security-operations
  text; expectation is low scores (recorded, not asserted as empty).
- Proposal (UNAPPROVED): `accept`, high — no technique described;
  elevated top score is lexical attraction, not label error.
- Recorded retrieval (v2): max 0.4341 (T1685 family) — highest no-match
  score in either version.
- Question: confirm no-match; confirm score is lexical attraction.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N01 — spreadsheet help (v1 + v2 records) — no-match

- Query: "How do I fix the quarterly budget spreadsheet formulas in Excel?"
- Expected: no-match (recorded max 0.2212).
- Proposal (UNAPPROVED): `accept`, high.
- Question: routine no-match confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N02 — onboarding chatter (v1 + v2 records) — no-match

- Query: "Employee onboarding schedule for the new office kitchen renovation next month."
- Expected: no-match (recorded max 0.2517).
- Proposal (UNAPPROVED): `accept`, high.
- Question: routine no-match confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N03 — facilities request (v2 record only) — no-match

- Query: "The printer on the third floor is jammed again, please send a replacement toner cartridge."
- Expected: no-match (recorded max 0.3061).
- Proposal (UNAPPROVED): `accept`, high.
- Question: routine no-match confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N04 — SQL help (v2 record only) — no-match

- Query: "How do I write a SQL JOIN to combine the customers and orders tables?"
- Expected: no-match (recorded max 0.1956; technical-but-irrelevant probe).
- Proposal (UNAPPROVED): `accept`, high.
- Question: routine no-match confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N05 — team chatter (v2 record only) — no-match

- Query: "Photos from the team offsite last weekend are in the shared album."
- Expected: no-match (recorded max 0.2771; low-information probe).
- Proposal (UNAPPROVED): `accept`, high.
- Question: routine no-match confirmation (note low-information framing).
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N06 — Jenkins restart (v2 record only) — no-match, borderline wording

- Query: "Restart the Jenkins build agent on the Windows build server after patching."
- Expected: no-match. Rationale (fixture): routine admin action without
  malicious intent; may lexically resemble execution/persistence content.
  Ambiguity (fixture): borderline administrative action.
- Proposal (UNAPPROVED): `accept`, medium.
- Recorded retrieval (v2): max 0.1859 (lowest benign max).
- Question: confirm benign-administrative reading; confirmed no-match vs
  insufficient-evidence?
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N07 — sales prose (v2 record only) — no-match

- Query: "Quarterly sales figures rose twelve percent year over year, beating the forecast."
- Expected: no-match (recorded max 0.1356).
- Proposal (UNAPPROVED): `accept`, high.
- Question: routine no-match confirmation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

### RB-N08 — degenerate input (v2 record only) — no-match

- Query: "the"
- Expected: no-match. Rationale (fixture): degenerate single-stopword
  probe of worst-case score behavior (recorded max 0.1781), not correctness.
- Proposal (UNAPPROVED): `accept`, medium.
- Question: confirm degenerate-input framing and no-match as the only
  honest expectation.
- Reviewer: identity ___ / qualification ___ / date ___ /
  decision ___ / rationale ___ / evidence refs ___.

## 9. Queue adequacy and smallest additive extension (proposed, NOT implemented)

The existing queue (`rag_label_review_v1.json` + `validate_review_queue`)
is adequate as the system of record for starting review: stable IDs,
source linkage with byte-equality enforcement, machine/human separation,
pending-vs-decided explicitness, and 11 passing integrity tests. No new
database, service, or dependency is needed.

Gaps found against §§4–5 requirements, with the smallest additive,
backward-compatible extension proposed (all fields optional, so all 42
current records keep validating; to be implemented only after
project-owner approval — **not implemented in this phase**):

1. **Reviewer qualification/role.** The `reviewer` block has `identity`
   but no qualification field. Proposed: optional `reviewer.qualification`
   (free string, e.g. "ATT&CK taxonomy", "SOC analyst L2"). Until then,
   record qualification as the first line of `reviewer.rationale`.
2. **Evidence references.** No field for URLs/citations. Proposed:
   optional `reviewer.evidence_refs` (list of strings). Until then, cite
   sources inline in `reviewer.rationale` (this guide's §8 gives the
   already-verified references per case).
3. **Structured revised labels.** A `revise` decision currently lands in
   free-text `proposed_change.detail`. Proposed: optional
   `reviewer.decided_ids` (list of T-IDs) + `reviewer.decided_no_match`
   (boolean), required by the validator exactly when `decision: revise`.
   Until then, state the exact replacement set verbatim in
   `proposed_change.detail` (and keep the machine's unapproved suggestion
   untouched beside it).
4. **Ambiguous-vs-escalation wording.** `needs-domain-review` covers both
   terminal ambiguity and escalation-to-expert (disambiguated in
   rationale, §5.1). If reviewers find this confusing in practice, the
   smallest change is one additive decision value (e.g. `ambiguous`), not
   a redesign. No change proposed now — revisit only on reviewer request.

No reviewer workflow may infer that an AI proposal is authoritative: the
validator pins `automated_proposal.analyzer` to `"automated-analysis"` and
rejects any other attribution.

## 10. DI-001 completion protocol (what still requires real review)

DI-001 stays open until **all** of the following are recorded; this guide
prepares the workflow but satisfies none of them:

- **Coverage:** all 42 queue records `decided` with full reviewer blocks
  (25 unique scenarios; shared scenarios recorded in both version records).
- **Reviewer qualifications:** at least the taxonomy-escalated cases
  (RB-014 known; any case ending in `revise` across tactic families)
  decided or countersigned by an ATT&CK-qualified reviewer. The minimum
  number and mix of reviewers is **not set here — project-owner decision
  required** (no arbitrary count is invented in this phase).
- **No-match cases:** each confirmed (or re-framed) with the benign /
  insufficient-context reading stated, not merely score-observed.
- **Ambiguous cases and disagreements:** left explicitly `needs-domain-review`
  with positions and missing evidence named; never forced to consensus.
- **Evidence and provenance:** corpus definition citations minimum; Tier-1
  official pages for every `revise` and every taxonomy dispute; reviewer
  identity + date per record (fixture provenance).
- **Approval:** review owner (project owner or delegated lead) signs off
  that the decided queue satisfies the above; the sign-off identity is
  recorded with the adjudication commit.
- **Versioning:** adjudicated labels ship as a **new versioned benchmark**
  (e.g. `rag-benchmark-v3` or v1.1/v2.1 pair) plus a migrated review
  queue; v1/v2 fixtures and both saved baselines remain byte-identical
  reference points forever.
- **Evaluation:** the adjudicated benchmark is evaluated into **new**
  baseline files; existing `rag_baseline_v1/v2.json` are never overwritten,
  and the P1-14 gate continues to guard v1/v2 retrieval changes on the
  original references.

## 11. Integrity record for this phase

- Benchmark fixtures, review queue, baselines, corpus fingerprints,
  retrieval code, thresholds, FAISS/embedding artifacts: **unchanged**.
  (`git status` shows no modification to any of these paths.)
- Baselines were **not** rerun or overwritten to prepare this packet.
- No review decision was fabricated: queue remains 42 pending / 0 decided.
- No commit or push was made.
- Full file hashes (sha256, 2026-10-12): benchmark v1
  `9314852a36a340fe167088288253182ab2896c339835a155a2b7f4986bd3e5b6`;
  benchmark v2 `7a77a797cffdf15fb590963b4d1f65fe40697472e659b59146e46cf77d`;
  review queue `8c10fc81cbbf9a90e600eb5e206d178e38bd1d6a8819c0cd9212a13ee9ca4852`;
  baseline v1 `d131aaf60e07abe03fed7caf2c0a8c16ff6ee37fd0e4cdd75359a0eeb754ea8c`;
  baseline v2 `1d65e33b84c3f01d1bccef2d4ca69c8b9624d9bdfc022a67b3d6980b00e1574b`.

## 12. File pointers

- Benchmarks: `backend/tests/fixtures/rag_benchmark_v1.json`,
  `backend/tests/fixtures/rag_benchmark_v2.json`
- Review queue (system of record): `backend/tests/fixtures/rag_label_review_v1.json`
- Saved baselines (reference, read-only): `backend/tests/fixtures/rag_baseline_v1.json`,
  `backend/tests/fixtures/rag_baseline_v2.json`
- Label audit: `docs/reliability/RAG_BENCHMARK_LABEL_AUDIT.md`
- Evidence packet: `docs/reliability/RAG_ATTACK_EVIDENCE_REVIEW.md`
- Queue validator: `backend/app/services/rag_evaluation.py`
  (`validate_review_queue`, `REVIEW_DECISIONS`, `REVIEW_STATUSES`)
- Queue integrity tests: `backend/tests/unit/test_label_review.py`
- Comparison gate (P1-14, retrieval-change workflow; untouched):
  `scripts/check_rag_baseline.py`,
  `backend/tests/unit/test_baseline_gate.py`
