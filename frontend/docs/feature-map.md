# Feature Map (P-1)

Real backend exposes only: GET /api/v1/health, POST /api/v1/detect, POST /api/v1/detect/batch.
Status: Supported (wired) / Derived (client-side from supported data) / SAMPLE (no backend source).

| UI element | Backend endpoint / field | Status |
|---|---|---|
| Dashboard "Detection Active" status pill | GET /api/v1/health → status/model_status | Supported |
| Detection Details score gauge, severity | POST /api/v1/detect → detection.anomaly_score, severity.level | Supported |
| Flow JSON panel | request flow fields + POST /api/v1/detect metadata | Supported |
| Feature importance | — none (README: per-feature attribution not fabricated) | SAMPLE |
| MITRE technique / related / confidence | attack_context.mitre_techniques always [] | SAMPLE |
| AI analysis, recommended actions | explanation.summary/reasoning/recommendations are null/[] | SAMPLE |
| KPI values (flows, anomalies, critical, accuracy) | — none | SAMPLE |
| Dashboard charts (activity, severity donut, attack types) | — none; derived from mock detection list | SAMPLE |
| Recent detections table | — none | SAMPLE dataset, wired through adapters |
| System Status card | GET /api/v1/health → mapped; other rows SAMPLE | Mixed |
| Analytics charts, top source IPs, report sections, PDF export | — none (export generated client-side) | SAMPLE |
| Landing pipeline demo sample JSON (3 flows × 7 stages) | — static demo data; stage scores could optionally call /detect | SAMPLE (demo by design) |
| Detection-time, type, IPs, protocol/ports of a detection | — none | SAMPLE |
| Live demo "Pause/Resume" | client-side only | Derived |
| Date-range pill "Sep 14, 2026 - Sep 20, 2026" | — none | SAMPLE static |

Additions beyond spec images (documented): none yet; stateless POST /api/v1/detect/batch could back the Detection page's flow input later.

Real data wins: any component that can call /detect or /health uses real responses via adapters; SAMPLE items keep the exact copy/layout from the spec.
