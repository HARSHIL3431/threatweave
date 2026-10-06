# Old Frontend Audit (P-1)

Stack: React 18 + Vite 5 + TS, axios, @tanstack/react-query, zustand, react-router-dom 6, recharts, framer-motion, lucide-react, Tailwind 3.

- API layer: `src/api/client.ts` (axios instance, baseURL `VITE_API_BASE_URL`, dev proxy `/api -> http://localhost:8001` in `vite.config.ts`, 30s timeout, correlation-ID interceptor, normalized error mapping), `health.ts`, `detection.ts`, `explain.ts`, `reports.ts`.
- Env: `.env` → `VITE_API_BASE_URL=http://localhost:8001/api`, dev proxy to 8001.
- Pages: LandingPage, DashboardPage, DetectionPage, AnalyticsPage, MitrePage, SettingsPage, DocumentationPage, HelpPage, NotFoundPage.
- Real backend usage: health check, single detection, batch detection. Everything else (analytics charts, MITRE page, reports, docs) is mock data under `src/data/mock/*`.
- Works and must not be lost: vite proxy pattern to backend (new app uses Next rewrites instead), typed API layer with normalized errors, health/degraded fallback handling, sample flow presets in `src/data/sampleFlows.ts`, ThemeContext with persistence.
- Do NOT copy: its code, structure, styling, or mock-first approach.
