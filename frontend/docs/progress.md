# Progress Log

## P-1 Audit — DONE
- Safety: copied 10 images to `demo\design-reference\threatweave-ui\` (verified, 10 files), into `frontend-new\docs\reference\`, zipped old frontend to `demo\_backup\frontend-old-2026-10-06.zip` (node_modules excluded, ~15.6MB).
- Backend started on port 8001 with logs/PID in `frontend-new\logs\` (backend folder kept clean; stray server.log files removed, verified).
- Real responses captured in `docs/evidence/` (health, 3× detect, batch, 422 error).
- Docs written: `docs/backend-audit.md`, `docs/old-frontend-audit.md`, `docs/feature-map.md`.
- Key finding: backend supports only health + detect + detect/batch; all dashboard/analytics/MITRE/feature-importance/report data is SAMPLE via adapters.

## P0 — DONE
- Next.js 16.3.8 (App Router, TS, Tailwind v4) scaffolded into `frontend-new` (via temp dir merge, docs/ and logs/ preserved).
- Deps: next-themes, recharts, framer-motion, lucide-react, clsx, tailwind-merge, cva, @radix-ui/react-slot; @playwright/test pinned to 1.62.1 (chromium-1234 already cached; v1243 download fails on flaky network).
- Created: `src/styles/tokens.css`, globals.css wiring tokens, Inter/JetBrains Mono/Caveat fonts via next/font, ThemeProvider (class strategy, default dark, system), next.config rewrites `/api/* → http://localhost:8001/api/*`, `src/lib/types.ts`, `src/lib/api/{client,backend}.ts`, `src/lib/data/detections.ts` (SAMPLE mock dataset + aggregates), brand components (Logo, EyebrowBadge, TwoToneHeading, ThemeToggle), ui primitives (Button, GlassCard, IconTile, StepCard, CodeBlock, SeverityBadge, TechniqueChip, ConfidenceBadge, StatusPill), `src/components/charts/charts.tsx` (Sparkline, DonutChart, BarList, TrendChart, Gauge), `scripts/shot.js`.
- Gate evidence:
  - `npx tsc --noEmit` → zero errors.
  - `npm run lint` → zero errors (fixed react-hooks setState-in-effect on theme-toggle using useSyncExternalStore).
  - `npm run build` → ✓ Compiled successfully, routes /, /_not-found, /dev/components prerendered.
  - Screenshots: `docs/screenshots/p0/dev-components-dark.png`, `docs/screenshots/p0/dev-components-light.png` (both themes render, charts + tokens working).
- Console errors: none captured in dev server log during screenshots.

## P1 — DONE
- Plan: landing sections 1–3 (Navbar, Hero, HowItWorks, LiveDemo), real-token styling, zero component-side hex (charts use var tokens; code blocks stay #0A1120 dark by spec).
- Files: `src/app/(marketing)/page.tsx`, `components/landing/{navbar,hero,how-it-works,live-demo}.tsx`, `src/lib/data/demoFlows.ts` (3 flows × 7 stages).
- Gate evidence: `npm run lint` zero errors (after key-prop fix via `scripts/fix-keys.py`, eslint ignores `scripts/**`, useTheme unused import removed); `npx tsc --noEmit` clean after `npm run build`; `npm run build` ✓ Compiled successfully (routes /, /_not-found, /dev/components).
- Screenshots: `docs/screenshots/p1/landing1-dark.png`, `docs/screenshots/p1/landing1-light.png` (script `scripts/shot.js`, console errors: []).
- Deviations vs reference (justified): globe is a dotted-SVG approximation (no land data), wave terrain omitted, How-It-Works row scrolls horizontally under 1536px width showing 6 of 7 cards.
- Snapshot: `demo\_snapshots\p0` (and p1 taken at P2 start).

## P2 — DONE
- Files: `components/landing/{product-demo,capabilities,mitre-ai,final-cta,footer}.tsx`.
- Evidence: lint 0 errors, build ✓, screenshots `docs/screenshots/p2/landing-{dark,light}.png`, `console errors: []`, snapshot `demo\_snapshots\p2`.
- Deviations: laptop mockup shows a placeholder "Dashboard preview" (real dashboard screenshot to be swapped); "Watch Full Demo" buttons are inert (no video asset available); footer brand icons use lucide Globe/Link/Video because brand icons were removed from lucide-react 1.x.

## P3 — DONE
- Plan: app shell (sidebar+topbar) with nav items, Dashboard wired to MOCK dataset + live `/api/v1/health` for System Status.
- Files: `src/app/(app)/layout.tsx`, `components/app/{sidebar,topbar,kpi-card,detections-table,coming-soon}.tsx`, `lib/use-health.ts`, `src/app/(app)/dashboard/page.tsx`, coming-soon routes (mitre/reports/explorer/settings).
- Evidence: lint 0 errors, tsc clean, build ✓ (routes /, /dashboard, /detections/[id], /analytics, coming-soon pages, /dev/components). Screenshots `docs/screenshots/p3/dashboard-{dark,light}.png`, `console errors: []`.
- Ctrl/Cmd+K focuses search (document-level keydown, tested by code inspection; no console errors).

## P4 — DONE
- Files: `src/app/(app)/detections/[id]/page.tsx` (prev/next, PDF export via jspdf, feature-importance bars, MITRE panel, AI analysis panel), `src/app/(app)/analytics/page.tsx` (KPIs, trend, donut, top IPs, detections table, report panel with tabs/sections/PDF).
- Evidence: lint 0 errors/0 warnings; build ✓ all routes; screenshots `docs/screenshots/p4/detection-{dark,light}.png`, `analytics-{dark,light}.png`, `console errors: []`.
- Sidebar active state: dark = red gradient (preserved), light = pale-red fill + red text via `@custom-variant dark (&:where(.dark, .dark *))` in globals.css; re-shot with `console errors: []`.

## P6 — Cutover DONE
- Stopped dev server (PID 14768 killed) and backend (PID 31544) so file handles released; deleted old `demo\frontend` (backup zip verified: `demo\_backup\frontend-old-2026-10-06.zip`, 15.6MB, 10 reference images preserved in `demo\design-reference\threatweave-ui\`).
- Renamed `frontend-new` → `frontend`. Rename failed twice (locked): root cause was the backend process holding `frontend-new\logs\backend.{out,err}.log` open (its stdout/stderr were redirected there) plus stale node processes. Fixed by killing stale node processes, moving logs, stopping the backend, then robocopy /MOVE + removing leftover `frontend-new`.
- Backend restarted with logs/PID in `frontend\logs\`, health: `{"status":"healthy","model_status":"ready",...}`.
- Dev server restarted from `demo\frontend` (`logs\frontend.dev.log`); `GET /` 200, `GET /api/v1/health` via Next rewrites: 200 healthy.
- Final gate from final location: `npm run lint` 0 errors/0 warnings; `npm run build` ✓ (11 routes); `node scripts\smoke-api.cjs` all PASS; `node scripts\smoke-ui.cjs` 9 routes × 2 themes all PASS, zero console errors; screenshots in `docs\frontend\screenshots`→`docs\screenshots\smoke\`.

## P5 — DONE
- Responsive spot-check: `docs/screenshots/p5/dashboard-1280-dark.png`, `docs/screenshots/p5/dashboard-768-dark.png` (layout stacks, sidebar hidden, no console errors).
- UI smoke suite (`scripts/smoke-ui.cjs`): all 9 routes × 2 themes → PASS, status 200, zero console errors, key text present; screenshots in `docs/screenshots/smoke/`.
- API smoke suite (`scripts/smoke-api.cjs`): health/detect×3/batch/invalid-422 → all PASS (scores match fixture expectations: 0.451762/info, 0.540229/medium, 0.458718/info).




