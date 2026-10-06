# THREATWEAVE — Final Report (A.7)

## 1. Run commands (Windows PowerShell)

Backend (port 8001):
```powershell
cd C:\Users\Admin\Desktop\demo\backend
python -m uvicorn app.main:app --port 8001
# logs/PID: C:\Users\Admin\Desktop\demo\frontend\logs\backend.{out,err}.log / backend.pid
```

Frontend (Next.js dev, port 3000):
```powershell
cd C:\Users\Admin\Desktop\demo\frontend
npm install        # first time only
npm run dev
# prod: npm run build && npm run start
```

Environment: `frontend\.env.example`
```
NEXT_PUBLIC_API_BASE_URL=/api   # Next rewrites proxy /api/* -> http://localhost:8001/api/*
USE_MOCK=false / NEXT_PUBLIC_USE_MOCK=false
```

## 2. Final raw A.5 evidence (from `C:\Users\Admin\Desktop\demo\frontend`)

- `npm run lint` → 0 errors, 0 warnings.
- `npm run build` → ✓ Compiled successfully; 11 routes (`/`, `/analytics`, `/dashboard`, `/detections/[id]`, `/dev/components`, `/explorer`, `/mitre`, `/reports`, `/settings`, `/_not-found`).
- `node scripts\smoke-api.cjs`:
  ```
  health: PASS healthy ready
  detect benign_flow: PASS 200 0.451762 info
  detect anomalous_flow: PASS 200 0.540229 medium
  detect zero_duration_flow: PASS 200 0.458718 info
  detect/batch: PASS 200 2
  invalid input -> 422: PASS 422
  ```
- `node scripts\smoke-ui.cjs`: all 9 routes × 2 themes PASS (status 200, 0 console errors, key text present). Screenshots: `frontend\docs\screenshots\smoke\`.
- `backend\GET /api/v1/health` (via frontend rewrite): `{"status":"healthy","model_status":"ready","model_version":"isolation_forest_v1","experiment_id":"with_port","active_operating_point":"OP-A","active_threshold":0.521919,...}`.
- Sample generated PDF: `frontend\docs\sample-incident-report.pdf`.

## 3. Feature map

See `frontend\docs\feature-map.md`. Status summary: health→System Status (Supported), detection score/severity→details page (Supported), detect/batch used by smoke tests (Supported); everything else (KPIs, charts, detections table, MITRE panels, feature importance, AI analysis, PDF content, dates) is **SAMPLE** via typed mocks in `src/lib/data/detections.ts` / `src/lib/data/demoFlows.ts`, marked `// SAMPLE` in code and in the map.

## 4. SAMPLE items (backend gaps worth fixing later)

- No endpoints for: detection history/list, aggregate KPIs, time-series activity, severity/attack-type distribution, top source IPs, per-feature importance attribution (README explicitly says it is not fabricated), MITRE technique lookup (stub returns `[]`), LLM explanations (stub returns null), report/PDF generation.
- `severity.level` is a documented placeholder calibration; MITRE/RAG/LLM services are disabled no-op stubs.

## 5. Backend untouched

`backend/` contains no edits — only read (README, fixtures) and runtime (uvicorn on :8001). No files added/removed there. Logs and PID live only in `frontend\logs\`.

## 6. Old frontend / design-reference / backups

- Old `frontend` deleted at cutover (P6). Backup: `demo\_backup\frontend-old-2026-10-06.zip` (~15.6MB, node_modules excluded).
- `design-reference` preserved at `demo\design-reference\threatweave-ui\` (10 PNGs + DESIGN_SYSTEM.md/README.md copies) and `frontend\docs\reference\`.
- File snapshots per phase: `demo\_snapshots\p0..p4`.

## 7. Cutover notes / deviations

- Old `frontend` was Vite/React; new app is Next.js 16 + Tailwind v4, route structure per spec sections 5–6.
- Theme: next-themes, class strategy, default dark, system on first visit; sidebar active item red-gradient in dark, pale-red in light.
- Known deviations logged in `docs\progress.md` (globe is a dotted-SVG approximation, no wave terrain, laptop uses placeholder, demo video buttons inert, brand icons substituted).
- `scripts/smoke-api.cjs` prints a harmless Node Windows async assertion on exit.

## 8. Uncommitted changes (`git status`)

Run `git status` in `C:\Users\Admin\Desktop\demo` — all work is uncommitted for review: deleted `frontend/` (old), added `frontend/` (new), `design-reference/`, `_backup/`, `_snapshots/`, modified nothing in `backend/`.
