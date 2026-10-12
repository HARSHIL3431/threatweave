# MITRE ATT&CK Index Rebuild Authorization Plan (P1-30, DI-004)

Read-only investigation. **The rebuild is NOT authorized.** No index,
metadata, benchmark, baseline, queue, detector, or retrieval artifact was
touched; nothing was downloaded.

## A. Executive decision: BLOCKED pending owner decisions

A rebuild cannot be authorized in this phase: no target release is
selected, no source snapshot is approved, no activation decision exists,
and no authorized reviewer is designated (§C). The existing production
index — stale-provenance but integrity-validated and load-bearing for all
recorded baselines — stays in service.

## B. Current-state evidence table

| Component | Observed state | Evidence source | Confidence | Unresolved question |
|---|---|---|---|---|
| Source URL | `raw.githubusercontent.com/mitre/cti` `master` `enterprise-attack.json` — a **moving target**, unpinned | `config.py:32-34`, `build_mitre_index.py:73-74` | fact (code) | Which pinned release should be the target? |
| Download verification | None: whatever `master` serves is written to disk; no approved-hash check | `build_mitre_index.py:29-47` | fact (code) | Approved snapshot hash (owner must supply out-of-band) |
| On-disk raw bundle | 47,953,963 bytes, sha256 `f7eaf37f…`, 26,085 objects, 858 attack-patterns, modified 2025-04-15→2026-08-04 | read-only inspection of `data/mitre/raw/enterprise-attack.json` | fact (artifact) | When/by what was it downloaded; whether it matches any release |
| Release mapping | Unmappable from bundle: no bundle-level release id (`extract_attack_version` returns None by design; `x_mitre_version` is per-object revision, spec version is schema) | `mitre_provenance.py:74-85`, builder prints "release version: unknown" (`build_mitre_index.py:172`) | fact (code) | Target release must come from the owner, not inference |
| Production index | 697 docs (222 techniques + 475 sub-techniques), 384-dim MiniLM-L6-v2, `index.faiss` 1,070,637 bytes; docs sorted by ID, no duplicates | `metadata.json` + code (`mitre_data.py:201`, `vector_store.py`) | fact (artifact+code) | — |
| Production provenance | **Absent**: no `provenance` block in metadata → status reports `built_at: null`, age `unknown` (a `created_at: 2026-09-20` file timestamp exists but is *not* provenance and is never presented as such) | `metadata.json`, `rag_service.py:328-352` | fact (artifact+code) | — |
| Bundle-vs-index gap | 858 on-disk patterns vs 697 indexed (revoked/deprecated excluded by design; ID-less objects skipped) | `mitre_data.py:129-201`, counts above | fact (code+artifact) | Exact exclusion ledger for the current index is not recorded |
| Write atomicity | Per-file atomic (`os.replace` of temp files) but **not pair-atomic**: crash between the two replaces leaves a mismatched pair | `vector_store.py:99-126` | fact (code) | Mitigated by loader alignment checks (fail closed) |
| Absent/malformed/stale provenance | Loads anyway as unknown (`provenance=None`); age unknown (never fresh); stale only from valid `built_at` > 180d | `vector_store.py:263-265`, `mitre_provenance.py:120-141` | fact (code), tested | — |
| Rebuild determinism | Documents deterministic (sorted IDs); embeddings/model-version dependent; a rebuild from the on-disk bundle would change counts, IDs present, ordering positions, vectors, and rankings vs production | `build_mitre_index.py:15-16`, `mitre_data.py:194-201` | fact (code) + inference flagged as such | Byte-reproducibility of a rebuild is unverified |
| Deployment/activation | Builder writes production paths directly (`settings.mitre_index_file`); **no staging, no activation gate** — running the script replaces what the app serves on next load | `build_mitre_index.py:149-165` | fact (code) | Staged candidate location + separate activation (owner) required |

Report-supported facts (not re-verified today): live catalog v19.2 as of
2026-10-11; T1685.005 created 2026-04-14 (consistent with, not proven by,
the on-disk modified range). The currently published release is **not**
assumed to be the rebuild target — new releases change techniques, IDs,
descriptions, and counts.

## C. Rebuild authorization checklist (all unresolved)

- [ ] Target ATT&CK release + official source (pinned, not `master`) — UNRESOLVED (owner)
- [ ] Approval to download/retain the exact source snapshot (bytes + sha256) — UNRESOLVED
- [ ] Approval to regenerate corpus/embeddings/index/metadata (isolated location) — UNRESOLVED
- [ ] Compatibility + regression checks defined (gate, integrity tests, frozen benchmark) — DEFINED in §D, not yet run
- [ ] Production activation authorized — UNRESOLVED (separate decision)
- [ ] Rollback owner + procedure — UNRESOLVED (proposal in §F)
- [ ] Sign-off identity + evidence retention location — UNRESOLVED
- [ ] N/A items: none (every item applies)

## D. Proposed safe rebuild sequence (specified, NOT executed)

1. **Pre-rebuild record**: hashes of index/metadata/bundle, git rev, baseline SHAs. *Fail:* any unreadable artifact → stop. *Approval:* no.
2. **Obtain approved snapshot** (pinned release URL or `--raw` local file) into an isolated directory, never production paths. *Fail:* non-200/unreadable → stop.
3. **Verify hash + release identity** against owner-supplied values. *Fail:* mismatch → discard, stop. *Approval:* values come from owner.
4. **Build candidate** with `--out <isolated>` (note: current builder ignores `--out` for processed/vectorstore paths — `settings`-derived; a rebuild phase must stage outputs or extend the flag; documented gap, no code changed here). *Fail:* parse/embedding errors → stop.
5. **Validate candidate**: schema, stable IDs, duplicate scan, counts vs exclusion ledger, 384-dim, vector norms ~1.0, FAISS dim, metadata↔vector alignment. *Fail:* any mismatch → discard.
6. **Provenance completeness**: all seven fields present, `attack_version` honestly null unless the release is independently established. *Fail:* incomplete → discard.
7. **Run integrity + RAG regression tests** (`test_vectorstore_integrity`, `test_rag_evaluation`, baseline-gate suite). *Fail:* test failure → discard.
8. **Baseline gate**: expected INCOMPATIBLE (fingerprint/sha change) — the gate's defined behavior for a new corpus, not a failure; record the incompatibility report.
9. **Frozen-benchmark retrieval comparison** on v1/v2 (interpreted: labels synthetic, 0 adjudicated — deltas are observations, not verdicts). *Fail:* errors/coverage loss → investigate.
10. **Document deltas**: added/removed IDs, changed descriptions, ranking shifts, failures, limitations.
11. **Separate activation authorization.** *Approval:* yes, distinct from build approval.
12. **Reversible activation**: keep previous index+metadata pair aside; swap pairs (never single files); verify load + status + gate-incompatible-expected; rollback = restore prior pair. *Fail at any check:* roll back.
13. **Post-activation health**: status, integrity counters, provenance age fresh.

## E. Benchmark and evaluation limitations

v1/v2 labels are synthetic, 0 of 42 adjudicated — a rebuild comparison
measures retrieval *movement*, never correctness. The P1-14 gate enforces
compatibility; a new corpus is incompatible by definition, so its report
is expected and must not be forced to pass. A release change requires an
explicitly versioned candidate benchmark/baseline pair; existing
`rag_baseline_v1/v2.json` are never overwritten to make a comparison pass.

## F. Failure and rollback analysis

Missing/unverifiable source version → stop (no inference). Hash mismatch
→ discard bytes, stop. Incomplete provenance → discard candidate. ID
duplicates/count/dimension mismatch → discard. Build failure → stop, keep
production. Gate incompatibility → expected, record. Unexpected ranking
shifts → document, owner judges. Partial replacement → prevented by
pair-swap; loader alignment fails closed on any residual mismatch.
Activation failure → restore prior pair, verify status. **Fail closed
throughout: an unverified candidate never replaces production.**

## G. Decision record and next action

No approval exists; nothing was approved in this phase. Owner must review
§B evidence + §C checklist and supply: target release, snapshot hash,
build/activation approvals, rollback owner, sign-off identity. Blocked
until then. Work requiring no authorization: DI-001 adjudication (which
should precede activation — a rebuild after adjudication forces
re-validation), gate/test maintenance, candidate-benchmark versioning
design. A future rebuild phase is permitted only when §C is fully
approved and §D is executed verbatim with evidence retained.
