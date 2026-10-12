# DI-001 First Batch — Owner Handoff (P1-29)

**No authorized human reviewer is available in this environment, and no
approved review channel exists.** The only actor present is the AI agent,
which is explicitly forbidden from inventing reviewer identity, dates, or
decisions. **Zero decisions were recorded; the queue is byte-unchanged
(42 pending / 0 decided, sha `8c10fc81cbbf`).** This document is the
ready-to-use handoff package.

## 1. Batch cases and exact reviewer questions (transcribed from artifacts)

### RB-014 — taxonomy dispute (records: v1 + v2; one scenario judgment, recorded twice)

- Query: "An intruder deletes system event logs to erase evidence of their activity." Expected: [T1070].
- Retrieved: T1685.005 (0.6774), T1685.006, T1685.001, T1685.004, T1070.004 (0.5464).
- Collected evidence: T1070 (Stealth: selectively delete/modify artifacts
  to reduce presence indications) vs T1685.005 (Defense Impairment: clear
  Windows Event Logs via wevtutil/Event Viewer/PowerShell/direct deletion
  under `C:\Windows\System32\winevt\logs\`). Full quotes: evidence review §2.
- Unapproved machine suggestion: consider T1685-family credit — explicitly
  NOT approved, do not apply without sign-off.
- Reviewer question: single-label T1070 vs multi-label including T1685
  family; does the tactic framing matter; what precedent for rival cases?
- Required expertise: ATT&CK taxonomy. Relevance: both supported.
  Intent: supported-malicious. Attribution: not-applicable.
  Remediation: not-assessable (no recommendation under review).

### RB-016 — gray zone (record: v2 only)

- Query: "A user cannot log in after a password reset and the helpdesk says the account appears locked." Expected: [T1110].
- Retrieved: T1531 (0.4471), T1201, T1556, T1110.001 (0.3638), T1110 (0.3542).
- Reviewer question: ratify relevance-without-malice framing; is T1110 fit
  for purpose as a relevance probe; is the future `intent` annotation
  (DI-017) required? Note relevant hits score below benign RB-017's max.
- Relevance: T1110 relevant as retrieval probe. Intent: benign-authorized
  (likely) vs ambiguous — judge from query text alone. Attribution:
  not-applicable. Unapproved schema suggestion on file; label unchanged
  regardless.

### RB-017 — no-match under lexical attraction (record: v2 only)

- Query: "Scheduled antivirus scan completed overnight with no threats found on any workstation." Expected: no-match.
- Retrieved: T1685 (0.4341, highest no-match score either version),
  T1685.005, T1679, T1564.012, T1027.005.
- Reviewer question: confirm no technique is described and 0.4341 is
  lexical attraction, not a label defect. A no-match asserts nothing about
  corpus coverage.

## 2. Required reviewer expertise

RB-014: ATT&CK taxonomy expertise (or countersignature). RB-016/RB-017:
security-analyst judgment on intent vs relevance. All: ability to cite
technique definitions and record competing-technique reasoning.

## 3. Channel, identity, and sign-off requirements (owner decisions)

- Approved channel: **unspecified — owner must designate** (this task
  provides none; agent-executed edits are not an approved channel).
- Identity convention: reviewer identity + qualification/role +
  ISO date + decision + rationale per record (validator-enforced).
- Sign-off: owner or delegated lead approves the decided batch; identity
  recorded with the commit. Reviewer count, independence rules for
  ambiguous cases, and confidentiality handling: **owner decisions,
  all pending** (see decision pack §4).

## 4. Exact fields to complete (existing system, unchanged)

In `backend/tests/fixtures/rag_label_review_v1.json`, per record:
`reviewer.identity`, `reviewer.date`, `reviewer.decision` (accept /
revise / reject / needs-domain-review), `reviewer.rationale`
(evidence + rival-technique reasoning + retain/revise/unresolved
statement), and `status: pending → decided`. Leave `original`,
`synthetic`, and `automated_proposal` byte-identical. Validate with
`python -m pytest tests/unit/test_label_review.py -q` from `backend/`.
RB-014's decision goes in both version records with shared rationale.

## 5. Next steps after decisions

Decided batch → owner sign-off → continue remaining 39 records → versioned
benchmark + migrated queue (v1/v2 fixtures and baselines stay
byte-identical) → fresh baselines as new files → DI-003 gate →
DI-002/DI-012 policy work → DI-017 annotations. Three reviewed cases do
not approve anything else and do not close DI-001.

## 6. Explicit confirmation

No reviewer exists in this task; no identity, date, decision, or
rationale was invented; automated proposals were not converted; no other
case was approved; fixtures, baselines, retrieval, thresholds, and code
are untouched. DI-001 remains open with 0 of 42 decided.
