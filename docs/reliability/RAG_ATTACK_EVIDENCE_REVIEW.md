# RAG ATT&CK Evidence Review (P1-6/P1-7) — Source-Cited Packet for Analyst Adjudication

Automated research only. **Nothing here is expert approval**: every human-review
field in `rag_label_review_v1.json` remains `pending`, no benchmark label was
changed, and no baseline was regenerated. Facts (quoted official definitions)
are separated from automated interpretation throughout.

Access date for all live sources: **2026-10-11**.

## 1. Sources verified

| # | Technique | Official title | Source URL | Version / dates | Evidence class |
|---|---|---|---|---|---|
| S1 | T1070 | Indicator Removal | https://attack.mitre.org/techniques/T1070/ | Technique v3.0; created 2017-05-31; modified 2026-05-12; site content v19.2 | Tier-1 (live official page, fetched) |
| S2 | T1685.005 | Disable or Modify Tools: Clear Windows Event Logs | https://attack.mitre.org/techniques/T1685/005/ | Sub-technique v1.0; created 2026-04-14; modified 2026-05-12 | Tier-1 (live official page, fetched) |
| S3 | T1056.003 | Input Capture: Web Portal Capture | https://attack.mitre.org/techniques/T1056/003/ | Sub-technique v1.1; created 2020-02-11; modified 2026-05-12 | Tier-1 (live official page, fetched) |
| S4 | T1563.001 | Remote Service Session Hijacking: SSH Hijacking | https://attack.mitre.org/techniques/T1563/001/ | Sub-technique v1.1; created 2020-02-25; modified 2025-10-24 | Tier-1 (live official page, fetched) |
| S5 | T1569.002 | System Services: Service Execution | https://attack.mitre.org/techniques/T1569/002/ | Sub-technique v1.3; created 2020-03-10; modified 2026-05-12 | Tier-1 (live official page, fetched) |
| S6 | — | Version History (release calendar) | https://attack.mitre.org/resources/versions/ | Catalog uses major.minor; current release **v19.2 (2026-04-28 – current)** | Tier-1 (live official page, fetched) |
| S7 | Corpus bundle | Local `enterprise-attack.json` via `data/mitre/vectorstore/metadata.json` descriptions | Local file (P0-1 source URL: mitre/cti `enterprise-attack.json`) | Bundle release **unknown** (production index predates provenance) | Tier-2 (official MITRE STIX content, locally stored; live re-verification pending) |

Limitations: live pages reflect v19.2 (current); the local corpus is of
unknown vintage, so live definitions may postdate corpus text. Page
`Last Modified` dates concern live content, not the corpus. No STIX
`modified`-field audit was performed in this phase.

## 2. Priority review: RB-014

Query (exact): *"An intruder deletes system event logs to erase evidence of their activity."*
Expected label: T1070. Retrieved rival: T1685.005 (ranks 1–4, scores up to 0.677); credited T1070.004 only at rank 5.

### 2.1 Official definitions (facts, quoted)

- **T1070 (S1):** *"Adversaries may selectively delete or modify artifacts
  generated to reduce indications of their presence and blend in with
  legitimate activity."* Tactic: Stealth. Live sub-techniques: .003–.010
  (includes .004 File Deletion; .001/.002 absent from the live listing).
- **T1685.005 (S2):** *"Adversaries may clear Windows Event Logs to hide the
  activity of an intrusion"* via `wevtutil`, Event Viewer, PowerShell, or
  direct deletion under `C:\Windows\System32\winevt\logs\`. Sub-technique of
  T1685 (Disable or Modify Tools). Tactic: **Defense Impairment**
  (distinct from T1070's Stealth). Sibling T1685.001 covers *disabling*
  (vs clearing) Windows event logging.

### 2.2 Answers (interpretation, automated)

1. **Described behavior:** post-activity deletion/clearing of system event
   logs — prototypically Windows Event Logs, though the query names no platform.
2. **Support:** the query supports **both** T1070 (broad indicator-removal
   framing) and specifically T1685.005 (exact behavior match). Evidence is
   sufficient to decide relevance for both; insufficient to pick exactly one.
3. **Current label:** defensible but arguably **too narrow** — it excludes an
   officially defined, equally-or-more specific behavior. Not incorrect.
4. **Multi-label acceptance (T1070 + T1685.005, or T1685 parent) is justified**
   by the query and has precedent in this benchmark (RB-001/006/009).
   Ranking must play no role in this judgment: T1685.005's ranks 1–4 reflect
   lexical similarity, not taxonomy authority.
5. **Human decisions required:** (a) single vs multi-label for RB-014;
   (b) whether the Stealth-vs-Defense-Impairment tactical framing matters
   for the benchmark's purpose; (c) the precedent line between crediting
   overlapping rivals (here) versus distinct-mechanism rivals (RB-002's
   T1569.002, RB-009's T1563.001 — both officially distinct, see §3).

Status: **evidence-prepared** (taxonomy decision pending analyst).

## 3. Other flagged cases (evidence-prepared)

- **RB-001 → T1595/T1046.** Tier-2 corpus text supports both (scanning;
  service listing). No live-page contradiction sought; labels stand as
  directly supported. Human question: confirm dual-label acceptability.
- **RB-006 → T1053/T1547.** Tier-2 corpus text supports both (task
  scheduling; boot/logon autostart). T1053 retrieved rank 1. Human
  question: confirm dual-label acceptability.
- **RB-009 → T1021/T1570.** Tier-2 corpus text supports both. Tier-1 (S4):
  *"SSH Hijacking differs from use of SSH because it hijacks an existing
  SSH session rather than creating a new session using Valid Accounts."*
  The query describes credential login (new session) — officially distinct
  from the top-hit rival. Exclusions of T1563.001/T1078 confirmed sound.
- **RB-016 → T1110 (gray zone).** Corpus/OFFICIAL definition pattern for
  T1110 is guessing-based access attempts; a post-reset lockout involves no
  guessing. Relevance-only framing from the audit stands; malice is
  undecidable from the query. Human question: ratify relevance-without-
  malice framing and the proposed future `intent` annotation (DI-017).
- **RB-005/T1056.003.** Tier-1 (S3): *"install code on externally facing
  portals, such as a VPN login page, to capture and transmit credentials."*
  Distinct mechanism from guessing (T1110), same scenario. T1110-only label
  defensible; rival is scenario-neighbor, not label error.
- **RB-002/T1569.002.** Tier-1 (S5): *"abuse the Windows service control
  manager to **execute** malicious commands or payloads"* (Execution
  tactic) vs query's *listing services to identify targets* (discovery).
  Officially distinct behavior — lexical "service" overlap is a documented
  trap, not a label defect.
- **RB-N05, RB-N08, RB-017 + RB-N01–N04, N06–N07.** No-match labels stand
  on their face (no ATT&CK behavior described); scores are measurements,
  not correctness claims. RB-017's 0.434 top score is lexical attraction
  (T1685 family), consistent with the no-threshold pipeline. No source
  pages required; status **evidence-prepared** via rationale record.

Remaining match cases (RB-003/004/007/008/011/012/013/015): Tier-2 corpus
definitions directly support each expected ID (verified texts on file);
rank-1 or policy-credited retrieval in 6 of 9. Marked **evidence-prepared**;
live-page re-verification is future work, not a blocker (recorded below).

## 4. Facts vs interpretations

Facts: quoted definitions, IDs, titles, tactics, versions, dates, URLs,
recorded scores/ranks, and the baseline numbers above are
observed evidence. Everything labeled "support", "defensible",
"arguably", "precedent", or "proposed" is automated interpretation for
analyst review — including this document's multi-label recommendation.

## 5. Unresolved questions (analyst-owned)

1. RB-014 single vs multi-label; T1685-family credit; Stealth vs
   Defense-Impairment relevance to benchmark purpose.
2. RB-016 relevance-without-malice ratification + `intent` annotation need.
3. Live-page re-verification of the nine Tier-2-only expected IDs.
4. Exact local-corpus release mapping (requires STIX content-date audit;
   T1685.005's 2026-04-14 creation date only *suggests* a v18.1+-era
   snapshot — inference, not fact).
5. All 42 review records still await human identity/date/decision/rationale.

## 6. Review-queue decision

No queue changes made: the validator schema has no evidence-reference
field, and the audit's traceability (case IDs + this document) suffices.
Human fields remain pending throughout. A future schema addition is
unnecessary unless analysts request inline evidence links.
