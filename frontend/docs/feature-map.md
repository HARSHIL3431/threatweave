# Feature Map (updated 2026-10-09)

Backend exposes 8 routes (see root `API_CONTRACT.md`): `GET /api/v1/health`, `POST /api/v1/detect`,
`POST /api/v1/detect/batch`, `GET /api/v1/rag/status`, `POST /api/v1/rag/query`, `POST /api/v1/explain`,
`POST /api/v1/reports/generate`, `GET /api/v1/reports/{id}/download` (all via the Next.js `/api` → `:8001` rewrite).
Status: Supported (live backend data) / Session (real responses stored in this browser only) / SAMPLE (no backend source).

| UI element | Backend endpoint / field | Status |
|---|---|---|
| Dashboard System Status + model metadata | GET /api/v1/health → status/model_status/rag_status/experiment_id/operating_point/threshold | Supported |
| Reports live workflow (flow → score → explanation → PDF) | POST /api/v1/detect, /explain, /reports/generate + download | Supported |
| MITRE search + index counts | GET /api/v1/rag/status, POST /api/v1/rag/query | Supported |
| Dashboard KPIs, session trend, severity donut, recent detections | Session store of live DetectionResponses (`lib/session-store.ts`) | Session |
| Detection Details for a session request id | Session store lookup by request_id | Session |
| Detection Details `d1`–`d5` | Fixture records in `lib/data/detections.ts` | SAMPLE (labeled; unknown ids → not-found) |
| Feature importance | — none (per-feature attribution not fabricated) | Unavailable (honest empty state) |
| Attack-type distribution, top source IPs | — none (backend never attributes attack types or stores history) | Unavailable (honest empty state) |
| Analytics export | Session records, source-labeled client-side PDF | Session |
| Landing pipeline demo sample JSON (3 flows × 7 stages) | Static demo data | SAMPLE (demo by design) |
| Live demo "Pause/Resume" | Client-side only | Derived |

Backend persists no detection history, so no KPI/chart can be global or cross-device; session metrics are
per-browser by design. Authoritative PDFs come only from `/reports/generate` + download.
