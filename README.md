# ThreatWeave — AI-Powered Security Anomaly Detection and Incident Intelligence Platform

Network flows → frozen Isolation Forest (E2 `with_port`) → severity → MITRE ATT&CK RAG → grounded LLM
explanation → dashboard → server-side PDF incident report.

## Quickstart (Windows PowerShell)

Backend (FastAPI, port 8001) — full local pipeline, no key, no cost:

```powershell
cd demo\backend
python -m pip install -r requirements.txt
$env:RAG_ENABLED='true'; $env:LLM_ENABLED='true'; $env:LLM_PROVIDER='mock'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Frontend (Next.js, port 3000; `/api/*` is rewritten to `http://localhost:8001/api/*`):

```powershell
cd demo\frontend
npm install   # first time only
npm run dev   # open http://localhost:3000
```

Then: Dashboard (live health) → Reports (score a sample flow → explanation → download backend PDF) →
MITRE (technique search). Health: <http://localhost:8001/api/v1/health>. API docs: <http://localhost:8001/docs>.

## What lives where

- `backend/` — FastAPI service (see `backend/README.md`). Stateless: detection, RAG, explanation, PDF reports.
  No database, no detection-history persistence.
- `frontend/` — Next.js 16 App Router UI. Session detection records live in browser localStorage only.
- `API_CONTRACT.md` — all 8 routes, schemas, error codes. `ARCHITECTURE.md` — services and data flow.
- `data/processed/experiments/with_port/` — **frozen** model + preprocessing config (OP-A `0.521919`).
- `THREATWEAVE_PHASE6_FINAL_AUDIT.md` — end-to-end verification report (PASS WITH LIMITATIONS).

## Tests

```powershell
cd demo\backend; python -m pytest tests -q        # 132 passed (87 unit + 45 integration)
cd demo\frontend; npx tsc --noEmit; npm run lint; npm run build
```

Notes: `requirements.txt` pins `httpx>=0.27.0,<0.28` (Starlette 0.36 `TestClient` compatibility — see
`TASKS.md`). Mock LLM output validates plumbing/grounding only, never real-LLM quality. Severity bands are
an explicit placeholder calibration, and retrieved ATT&CK techniques are candidates, not confirmed attacks.
