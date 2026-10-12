# RAG Benchmark Label Audit (P1-6) — Automated Analysis, NOT Expert Judgment

Scope: `rag_benchmark_v1.json` (17 cases) and `rag_benchmark_v2.json`
(25 cases: the 17 v1 cases byte-identical, plus RB-016/017 and RB-N03..N08).
All labels are synthetic; **no human review is recorded anywhere**.
Proposals below are automated analysis for analyst adjudication via
`backend/tests/fixtures/rag_label_review_v1.json` (42 records, all
`pending`). Nothing here changes benchmark labels, evaluator semantics,
or baselines.

Evidence used: benchmark fixture text, corpus technique definitions in
`data/mitre/vectorstore/metadata.json`, and recorded top-5 retrieval in
`rag_baseline_v1.json` / `rag_baseline_v2.json` (deterministic rerun
confirmed identical). No network fetching was performed; ATT&CK taxonomy
questions beyond local evidence are marked unresolved.

Reading guide per case: interpretation → mapping verdict → behavior class →
relevance-vs-malice → evidence needed → proposal.

## Shared technique-match cases (v1 § v2, identical payloads)

### RB-001 — port/ping sweep → [T1595, T1046]
Query: "An adversary probes the network with ping sweeps and port scans to find live hosts before attacking."
Behavior: explicit hostile reconnaissance (ping sweeps + port scans, stated pre-attack purpose).
Mapping: directly supported — T1595 Active Scanning covers probe-based recon; T1046 covers service listing. Multi-label is appropriate, not hedging.
Retrieval: total miss (top T1016.001/T1205/T1557 at 0.648). A retrieval failure, not a label error.
Class: malicious behavior, ambiguous across two valid techniques.
Relevance vs malice: both aligned (malicious + relevant).
Evidence needed: analyst confirms the dual-label acceptability.
Proposal: **accept** (high confidence, automated).

### RB-002 — remote service listing → [T1046]
Query: "Malware lists the services running on remote Windows hosts to identify vulnerable targets."
Behavior: malicious discovery, near-verbatim T1046 corpus language.
Mapping: directly supported. Retrieved T1569.002 (Service Execution — abusing SCM to *execute*, not list) is a lexical-overlap trap: same word "service", different behavior. This validates the label rather than undermining it.
Class: malicious, single technique. Proposal: **accept** (high).

### RB-003 — OS/hardware inventory → [T1082]
Rank-1 hit (0.632). Directly supported. Proposal: **accept** (high).

### RB-004 — LSASS hash dump → [T1003]
Rank-1 T1003.001 via parent/sub-technique policy. Directly supported. Proposal: **accept** (high).

### RB-005 — VPN password guessing → [T1110]
Behavior: high-volume guessing = Brute Force, directly supported. Retrieved T1056.003 (Web Portal Capture: code on VPN portals to steal entered credentials) is a genuinely nearby alternative mechanism for this exact scenario. The T1078 exclusion is correct scoping (use vs guessing). Proposal: **accept** (medium; nearby-alternative noted, not a defect).

### RB-006 — scheduled task at logon → [T1053, T1547]
T1053 rank 1. Retrieved T1543.001 (Launch Agent) and T1546 (Event Triggered Execution) are persistence-mechanism neighbors; T1547 absent top-5 but defensible for logon-triggered execution. Multi-label appropriate. Proposal: **accept** (high).

### RB-007 — PowerShell via interpreter → [T1059]
Rank-1 T1059.001. Directly supported. Proposal: **accept** (high).

### RB-008 — process injection → [T1055]
Rank-1 hit. Directly supported. Proposal: **accept** (high).

### RB-009 — SSH login + tool copy → [T1021, T1570]
Both expected IDs directly supported by corpus text; T1021 retrieved at rank 3. Top hit T1563.001 (SSH *Hijacking* — session theft, not credential login) is nearby but mechanistically distinct, confirming the T1078-adjacent scoping is meaningful. Proposal: **accept** (high).

### RB-010 — C2-channeled exfiltration → [T1041]
Directly supported. Retrieved T1027.006 (HTML Smuggling) and T1020 (Automated Exfiltration) are mechanism-adjacent misses. T1071 exclusion is correct scoping. Proposal: **accept** (high).

### RB-011 — passive sniffing → [T1040]
Rank-1 hit. Directly supported. Proposal: **accept** (high).

### RB-012 — local filesystem search → [T1005]
Near-verbatim T1005 corpus language; directly supported. Retrieved T1608.001/T1204.002 concern different attack stages despite "file" overlap — another lexical trap the label survives. Proposal: **accept** (high).

### RB-013 — keylogger → [T1056]
Rank-1 T1056.001. Directly supported. Proposal: **accept** (high).

### RB-014 — event-log deletion → [T1070] ⚠️ needs-domain-review
Directly supported by T1070 (Indicator Removal) corpus text — but retrieved T1685.005 (Clear Windows Event Logs, sub-technique of T1685 Disable or Modify Tools, ranks 1–4 at up to 0.677) is arguably an equally-or-more specific correct answer the label does not credit; the recorded R@5=1.0 rests solely on rank-5 T1070.004. Whether T1685-family answers are acceptable for event-log deletion is a genuine ATT&CK taxonomy question unresolvable from local evidence.
Class: malicious, single labeled technique with a credible unlabeled rival.
Proposal: **needs-domain-review** (medium). Suggested (NOT approved) change: consider crediting the T1685 family if taxonomy review supports it. Source verification needed: authoritative T1070-vs-T1685.005 scope guidance in a later authorized research pass.

### RB-015 — mail-server port fingerprinting → [T1046]
Directly supported; intentional thematic overlap with RB-001/002. Retrieval miss. Proposal: **accept** (high).

## Shared no-match cases (v1 § v2)

### RB-N01 / RB-N02 — spreadsheet help / onboarding chatter → no-match
Benign, non-technical/administrative, no ATT&CK content. Scores low (0.221/0.252). Labels honest: expectation is recorded scores, not emptiness. Proposal: **accept** (high).

## v2-only cases

### RB-016 — account lockout wording → [T1110] (gray zone)
Behavior: most likely a benign IT lockout; wording sits in credential-guessing retrieval space (T1110 retrieved, rank 4, R@5=1.0). Mapping: acceptable ONLY as a relevance probe — relevance must not be read as malice, as the fixture itself states. This is the benchmark's explicit relevance-vs-intent test.
Class: ambiguous intent by design.
Proposal: **accept** (medium) with the caveat preserved; schema suggestion (optional future `intent` annotation) recorded as a suggestion, not a change.

### RB-017 — benign AV scan → no-match
Benign security-operations text; top score 0.434 (T1685 family) — the highest no-match score in either version, demonstrating security-vocabulary attraction. Label honest (low-score expectation, recorded). Proposal: **accept** (high).

### RB-N03…N08 — facilities / SQL help / chatter / Jenkins restart / sales / "the" → no-match
Varied benign, technical-but-irrelevant, borderline-administrative (N06), and degenerate (N08) probes. All honestly framed as behavior measurements. Proposal: **accept** (high/medium as recorded per case).

## Coverage and integrity counts

- v1: 17 cases (15 technique-match, 2 no-match). v2: 25 cases (16 match, 9 no-match). Shared: 17 payloads byte-identical (verified programmatically). v2-specific: 8.
- Ambiguous-intent: RB-001, RB-006, RB-009 (multi-label), RB-016 (gray zone). Insufficient-context: RB-N08 (plus low-information RB-N05).
- Human review recorded: 0 of 25 unique cases (42 review records, all pending). Proposed label changes: 1 suggestion (RB-014, unapproved) + 1 schema suggestion (RB-016). Cases with sufficient evidence to approve now: 0 — approval requires a human analyst by definition.
- Baselines: v1 metrics P@5 0.253/R@5 0.600/MRR@5 0.536; v2 P@5 0.263/R@5 0.625/MRR@5 0.518. Deterministic rerun reproduced v2 exactly.

## Format expressiveness assessment

The benchmark has no intent/maliciousness dimension: `no_match` conflates "no technique described" (N01–N08, 017) with nothing about benign-vs-malicious. RB-016 carries its caveat in prose (`ambiguity` field) because no structured field exists. The evaluator contract needs no change for this; a future benchmark version could add an optional `intent` annotation. No format change is made here.

## Why current numbers prove nothing about production readiness

Synthetic labels (author-curated, n=25), 9 no-match samples cannot support a universal threshold (P1-4 measured misses outscoring hits), misses may be label-adjacent rather than wrong (RB-002/RB-005/RB-009/RB-014), and the 697-document index has unknown provenance/freshness — a separate, unresolved dimension (DI-004). Precision/recall/MRR here are regression tripwires for future retrieval changes, not quality certificates.

## What an analyst must supply to close DI-001

Per-case accept/revise/reject with identity, date, and rationale entered into `rag_label_review_v1.json` (schema enforced by `validate_review_queue`); T1070-vs-T1685.005 adjudication for RB-014; confirmation of the RB-016 relevance-only framing; and any re-labeling with authoritative ATT&CK citations from an authorized research pass.
