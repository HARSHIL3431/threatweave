# THREATWEAVE — PHASE 6 FINAL AUDIT

**Date:** 2026-10-09
**Branch:** `main` · **HEAD:** `c8719e89ae2457151f6361a492b9e6e4cecc371c` (unchanged before/after)
**Overall status:** `PASS WITH LIMITATIONS`
**Commits/pushes made:** none. No protected ML/backend files modified.

## A. Executive summary

The end-to-end intelligence pipeline is verified working against live services:

Network Flow → Frozen E2 Isolation Forest → Severity → MITRE RAG → Grounded mock-LLM explanation → Dashboard → Backend PDF report/download.

- **Verified:** frozen model identity and threshold, all 8 API routes over HTTP, exact fixture scores, controlled 422/404 errors, RAG retrieval with valid ATT&CK IDs, grounded mock explanations (IDs restricted to retrieved context), full PDF lifecycle (`%PDF-`, 3 pages, readable via pypdf), frontend typecheck/lint/build, 87 backend unit tests.
- **Manually verified (user, live services):** detection, explanation, PDF generation + download, MITRE search (222 techniques / 475 sub-techniques; “port scan …” query returns T1595, T1016.001, T1595.001, T1596.005 among 5 results).
- **Remains unverified/blocked:** backend *integration* suite (environmental Starlette/httpx incompatibility, unrelated to app code); real external LLM provider (no key configured — never tested, by policy); automated browser E2E (rely on manual verification instead).
- **Ready for a controlled demo:** yes, with `RAG_ENABLED=true LLM_ENABLED=true LLM_PROVIDER=mock` and both servers running (ports below).

## B. Repository integrity

- Branch `main`, HEAD `c8719e89ae2457151f6361a492b9e6e4cecc371c` before and after. No commit, push, stash, reset, branch change, or history rewrite.
- Initial `git status --short` (also final — nothing added/removed by this run):
  - Modified (pre-existing, preserved): `frontend/src/app/(app)/analytics/page.tsx`, `dashboard/page.tsx`, `detections/[id]/page.tsx`, `mitre/page.tsx`, `reports/page.tsx`, `frontend/src/lib/api/backend.ts`
  - Untracked (preserved): `frontend/public/Video/threatweave_demo_.mp4` (pre-existing media), `frontend/src/components/app/live-workflow.tsx`, `frontend/src/lib/data/liveSamples.ts`
  - No staged changes.
- Files modified **by this audit run:** exactly one — `THREATWEAVE_PHASE6_FINAL_AUDIT.md` (this report). No source-code fix was required (see §F).

## C. Architecture and integration

- **Ports:** backend `127.0.0.1:8001` (uvicorn), frontend `127.0.0.1:3000` (Next.js). Frontend `next.config.ts` rewrites `/api/:path*` → `http://localhost:8001/api/:path*`; `NEXT_PUBLIC_API_BASE_URL=/api`.
- **Verified routes** (from live `/openapi.json`, all exercised over HTTP): `GET /api/v1/health`, `POST /api/v1/detect`, `POST /api/v1/detect/batch`, `GET /api/v1/rag/status`, `POST /api/v1/rag/query`, `POST /api/v1/explain`, `POST /api/v1/reports/generate`, `GET /api/v1/reports/{report_id}/download`.
- **Model:** frozen E2 `with_port`, 60 features, `isolation_forest_v1`, OP-A threshold `0.5219193851693676` (artifact metadata read directly; seed 42, contamination 0.1, 502 981 Monday-benign train rows).
- **RAG:** MiniLM-L6-v2, 384-dim, 697 docs (222 techniques / 475 sub-techniques). Detection-time retrieval gated by `RAG_ENABLED`; standalone `/rag/*` works whenever the index exists.
- **Explanation:** via dedicated `/explain` only; detection never calls an LLM. `mock` provider is deterministic/offline; `openai` provider requires `LLM_API_KEY` (unset).
- **Reports:** server-side reportlab PDFs under `data/reports/`, UUID filenames, 32-hex ID validation on download, `application/pdf` MIME.

## D. Test evidence table

| ID | Component | Command / action | Expected | Actual | Verdict |
|----|-----------|------------------|----------|--------|---------|
| T01 | Frontend types | `npx tsc --noEmit` (frontend/) | clean | clean, exit 0 | PASS |
| T02 | Frontend lint | `npm run lint` | clean | clean, exit 0 | PASS |
| T03 | Frontend build | `npm run build` | success, 9 routes | success, 9 routes (`/`, `/dashboard`, `/detections/[id]`, `/analytics`, `/mitre`, `/reports`, `/explorer`, `/settings`, `/dev/components`) | PASS |
| T04 | Backend unit | `python -m pytest tests/unit -q` | pass | **87 passed** | PASS |
| T05 | Backend integration | `python -m pytest tests/integration/test_health.py -q` | pass | 1 failed + 2 errors: `TypeError: Client.__init__() got unexpected 'app'` — starlette 0.36.3 vs httpx 0.28.1 `TestClient` incompatibility | BLOCKED (environmental) |
| T06 | Health (HTTP) | `GET /api/v1/health` | healthy/ready | `healthy`, `ready`, `with_port`, OP-A, 0.521919, rag `ready` | PASS |
| T07 | Detect benign | `POST /detect` fixture | ~0.451762/info, `is_anomaly=false` | 0.451762/info/false | PASS |
| T08 | Detect anomalous | `POST /detect` fixture | ~0.540229/medium, `true` | 0.540229/medium/true (threshold rule score≥thr holds) | PASS |
| T09 | Detect zero-duration | `POST /detect` fixture | ~0.458718/info | 0.458718/info/false | PASS |
| T10 | Batch + empty | `POST /detect/batch` 2-flow / 0-flow | count 2 / count 0 | count 2 / count 0, order preserved | PASS |
| T11 | Invalid inputs | missing features / extra field / string type | controlled 422 | 3× `422 INVALID_INPUT` with structured body | PASS |
| T12 | RAG query | `POST /rag/query` “port scan …” | valid IDs | T1595 (0.52), T1016.001, T1595.001 … | PASS |
| T13 | RAG blank query | whitespace query | controlled 422 | 422 `INVALID_INPUT` | PASS |
| T14 | Explain (mock) | `POST /explain` anomalous | grounded, schema-valid | provider `mock`, ctx IDs `[T1011, T1016.001, T1030]` ⊆ retrieved top-3; limitations disclose mock + candidate-only status | PASS |
| T15 | Report+download | generate (with explanation) → download | `%PDF-`, non-empty | 8 880 bytes, `application/pdf`, 3 pages via pypdf; contains score, T1011, candidate-only wording, mock note | PASS |
| T16 | Bad report IDs | malformed + unknown 32-hex | controlled 404 | `404 REPORT_NOT_FOUND` (“Invalid report identifier” / “Report not found”) | PASS |
| T17 | Frontend up | `GET /` :3000 | 200 | 200 | PASS |
| T18–T21 | Manual E2E (user) | detection / explanation / PDF gen+download / MITRE search in browser | working | working; 222 tech / 475 subtech; 5-result port-scan query | MANUAL PASS |
| T22 | Real external LLM | n/a (no key; policy forbids fake keys) | — | NOT RUN | NOT RUN |
| T23 | Browser automation | existing `scripts/smoke-ui.cjs` | — | NOT RUN (manual verification used instead; no new tooling installed) | NOT RUN |

T06–T17 executed with real HTTP against the running backend (urllib) and by direct artifact/service inspection; T18–T21 are the user’s manual results, **not** automated passes.

## E. E2E workflow results

- **Detection:** PASS (manual + T07–T10). UI submits full 59-feature fixtures (`liveSamples.ts`, verbatim from backend fixtures) and renders backend score/threshold/severity; no fabrication path (mock mode throws `MOCK_MODE` instead of faking).
- **Explanation:** PASS (manual + T14). UI shows provider/model/latency, candidate-only technique list, limitations. Disabled-LLM path surfaces `LLM_UNAVAILABLE` text, never invented content.
- **PDF:** PASS (manual + T15). Frontend downloads the backend bytes (`downloadReport` fetches `/reports/{id}/download`); Reports page no longer uses the old client-side jsPDF stub for backend reports.
- **MITRE/RAG:** PASS (manual + T12). MITRE page shows live index status counts and renders real search results; blank query yields controlled 422 message.
- **Dashboard/sample integrity:** PASS by inspection — KPIs/charts carry SAMPLE labeling; System Status uses live health (`ML Model`, `RAG Index`, `API Services`) with remaining rows explicitly marked Sample. No “database connected” style false claim remains.

## F. Defects and fixes

No in-scope defect requiring a code change was confirmed by this run — **no source files were modified**. Root-cause notes for the two known issues (both left untouched per scope rules):

1. **Backend integration suite blocked (environmental, P2).** Cause: installed `starlette 0.36.3` vs `httpx 0.28.1` — `TestClient(app)` raises `TypeError`. App code is independently verified over real HTTP (§D). Minimal fix (needs approval): pin `httpx<0.28` for tests or upgrade `starlette`/`fastapi`; do not touch test assertions.
2. **Stale documentation (P3).** `ARCHITECTURE.md`, `API_CONTRACT.md`, `backend/README.md`, `TASKS.md` backlog, `frontend/docs/*` still describe a 3-endpoint stub backend and wrong ports. No doc rewrite performed (out of minimal scope); corrections listed in §I.

## G. Known limitations

- **Real backend:** detection, severity (explicit placeholder calibration), RAG retrieval, report PDFs.
- **Fixture/sample data:** dashboard KPIs/charts, detection-detail records, analytics aggregates are labeled SAMPLE mocks; `/reports` sample flows are real backend fixtures, not live captures.
- **Mock LLM:** deterministic, grounded, schema-validated — validates plumbing/grounding only, **not** real-LLM quality.
- **Real external LLM:** NOT RUN (no approved key; never use a real key just to pass).
- **Disabled-service behavior:** default env (`*_ENABLED=false`, no key) yields empty `attack_context` and `503 LLM_UNAVAILABLE` on `/explain` — by contract; detection unaffected.
- **Blocked:** backend integration tests (T05); automated browser suite (T23).

## H. Security and data-integrity findings

- No secrets in frontend: `NEXT_PUBLIC_*` carries only `/api` base + mock flags; `LLM_API_KEY` is server-side only; grep of `frontend/src` shows no keys/tokens (only false-positive “risk-based” substrings). Backend `.env` absent (only `.env.example` tracked); `.gitignore` covers `.env`, `*.pkl`, `*.faiss`, `data/reports/`.
- Report IDs server-generated UUIDs, strict 32-hex validation, confined to output dir — traversal test (`doesnotexist`, unknown hex) returns controlled 404s.
- Invalid/NaN/extra-field inputs → structured 422s; inference internals not leaked (`INFERENCE_ERROR` generic).
- Severity remains labeled `INITIAL PLACEHOLDER CALIBRATION`; anomaly ≠ confirmed compromise wording present in UI and PDF.
- No protected artifact/config changed (§L). No broad security certification claimed.

## I. Documentation discrepancies (recommended corrections, not applied)

- `ARCHITECTURE.md` / `API_CONTRACT.md` / `backend/README.md`: enumerate all 8 routes, RAG/LLM/report services, current schemas; remove “future stub” claims.
- `TASKS.md` backlog: RAG/MITRE/LLM/explanation/report items are implemented — move out of backlog.
- `frontend/docs/{feature-map,backend-audit}.md`: refresh endpoint list, ports, and mock-vs-live map.
- `FRONTEND_VERIFICATION.md` / `MEMORY.md`: stack is Next.js 16 (not React+Vite); update phase status.
- Port guidance: standardize backend `:8001` (matches frontend rewrite + smoke scripts) vs README’s `:8000`.

## J. Final readiness decision

**Controlled demo: YES.** Required setup: backend on `:8001` with `RAG_ENABLED=true LLM_ENABLED=true LLM_PROVIDER=mock` (full pipeline, zero cost, no key); frontend on `:3000` (`npm run dev` or `npm run start`). Proven end to end: health → detection (all 3 fixtures) → RAG search → grounded mock explanation → PDF generate/download, plus honest disabled-service and invalid-input handling. Before production: fix the test-client pin (T05), run the real-LLM evaluation with an approved key, refresh stale docs, and replace SAMPLE dashboard/detection content with real data sources.

## K. Reproduction instructions

```powershell
cd demo; git status --short   # expect §B listing; HEAD c8719e89
# Backend (full pipeline, mock LLM):
cd backend
$env:RAG_ENABLED='true'; $env:LLM_ENABLED='true'; $env:LLM_PROVIDER='mock'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
# Frontend:  cd ..\frontend; npm run dev   # http://localhost:3000
# Regression:
cd frontend; npx tsc --noEmit; npm run lint; npm run build
cd ..\backend; python -m pytest tests/unit -q   # 87 passed
# API probes:  GET /api/v1/health; POST /detect|/batch|/rag/query|/explain|/reports/generate (fixtures: backend/tests/fixtures/sample_flows.json)
```

## L. Git diff summary

This run changed **one file**: `THREATWEAVE_PHASE6_FINAL_AUDIT.md` (new). Pre-existing working-tree changes (preserved, not mine to commit): 6 modified frontend files wiring live health/detect/RAG/explain/reports with SAMPLE labeling (`analytics`, `dashboard`, `detections/[id]`, `mitre`, `reports` pages; `lib/api/backend.ts`) + 2 new frontend files (`components/app/live-workflow.tsx`, `lib/data/liveSamples.ts`) + 1 pre-existing untracked video. **Protected files unchanged:** no backend, model (`*.pkl`), preprocessing config, threshold, feature order, contract, or dependency file appears in the diff — confirmed via `git diff --name-only` (sole `backend|data|model` match is the frontend API client filename).
