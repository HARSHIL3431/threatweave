// MOCK DATA — replace with API integration later.
// Documentation page sections and honest development-state status labels.
// Status labels intentionally reflect what is implemented, verified, or
// still pending integration — nothing is claimed as live unless it is.

import {
  BrainCircuit,
  FileText,
  GitBranch,
  Network,
  BookOpen,
  ListFilter,
  Search,
  Workflow,
  Boxes,
} from 'lucide-react'
import type { DocSection } from './types'

export const docSections: DocSection[] = [
  {
    id: 'overview',
    title: 'Overview',
    icon: BookOpen,
    summary:
      'AI-powered platform that detects anomalous network flows using an Isolation Forest model trained on the CICIDS2017 dataset.',
    status: { label: 'IMPLEMENTED', variant: 'success' },
    body: 'The platform ingests CICIDS-style network flows, reproduces the frozen E2 preprocessing pipeline exactly, scores each flow with the frozen Isolation Forest model, and returns an anomaly score, a threshold decision and a placeholder severity classification. Intelligence layers (MITRE ATT&CK, RAG, LLM) sit behind it and, when active, add retrieved context and generated explanations without changing the ML decision.',
    bullets: [
      'Model: Isolation Forest (isolation_forest_v1, "with_port" experiment)',
      'Features: 60 CICIDS2017 features',
      'Serving: FastAPI backend at /api/v1',
      'Frontend: Vite + React + TypeScript shell with demo-data pages',
    ],
  },
  {
    id: 'architecture',
    title: 'Architecture',
    icon: GitBranch,
    summary:
      'Modular pipeline: flow validation → frozen preprocessing → ML scoring → severity → optional RAG/LLM intelligence layers → report generation.',
    status: { label: 'IMPLEMENTED', variant: 'success' },
    body: 'The backend is organised around single-responsibility services (ML, severity, RAG, LLM, report). The ML decision is fully autonomous and never depends on RAG or the LLM being reachable. The frontend mirrors this modularity with separate feature modules, a typed API layer and a centralized mock-data layer for the pages that are not yet powered by real backend endpoints.',
    bullets: [
      'Backend services: ml_service, severity_service, rag_service, llm_service, report_service',
      'Frontend modules: api/, features/, components/, data/mock/',
      'All mock pages keep real API integration as a drop-in replacement path',
    ],
  },
  {
    id: 'ml-detection',
    title: 'ML Detection',
    icon: BrainCircuit,
    summary:
      'Isolation Forest anomaly scoring with frozen E2 artifacts and operating-point thresholds.',
    status: { label: 'VERIFIED', variant: 'success' },
    body: 'The detector scores each flow with -model.score_samples(). Higher scores are more anomalous. A flow is flagged anomalous when its score is greater than or equal to the active operating threshold (OP-A = 0.521919 for the frozen model). The artifacts and preprocessing config are frozen, so results are deterministic and reproducible.',
    bullets: [
      'Score semantics: higher = more anomalous',
      'Operating points: OP-A (0.521919) and OP-B (0.487850)',
      'Frozen policy: no runtime threshold mutation',
      'Backend verified by the integration test suite',
    ],
  },
  {
    id: 'feature-pipeline',
    title: 'Feature Pipeline',
    icon: ListFilter,
    summary:
      'Reproduces the training preprocessing: zero-duration handling, log transformations, rate recomputation and exact 60-feature ordering.',
    status: { label: 'VERIFIED', variant: 'success' },
    body: 'Every incoming flow is validated against the E2 schema and transformed by the same pipeline used during training. The authoritative feature order and transformation list are loaded from preprocessing_config.json and validated against model metadata before any request is served.',
    bullets: [
      'Zero-duration handling (Is_Zero_Duration computed when omitted)',
      'Log1p transformations and rate recomputation',
      'Exact 60-feature ordering matching training',
      'Extra fields are rejected (422 Feature Mismatch)',
    ],
  },
  {
    id: 'mitre-rag',
    title: 'MITRE ATT&CK / RAG',
    icon: Search,
    summary:
      'Contextual retrieval maps flows to candidate ATT&CK techniques. Backend verified; frontend integration is pending.',
    status: { label: 'BACKEND VERIFIED / FRONTEND INTEGRATION PENDING', variant: 'warning' },
    body: 'The backend can retrieve candidate MITRE ATT&CK techniques relevant to a flow or natural-language query through the RAG endpoint. Retrieval results are candidates only ("retrieved-not-confirmed") and are never presented as confirmed attacks. The frontend currently shows honest placeholder states until the full retrieval loop is wired into the pages.',
    bullets: [
      'GET /api/v1/rag/status — index readiness',
      'POST /api/v1/rag/query — candidate retrieval',
      'Retrieved techniques do not confirm an attack',
      'Returns 503 RAG_UNAVAILABLE when the index is missing',
    ],
  },
  {
    id: 'llm-explanation',
    title: 'LLM Explanation',
    icon: BrainCircuit,
    summary:
      'Grounded structured explanations generated by the LLM endpoint. Backend implemented; API integration on the frontend is pending.',
    status: { label: 'IMPLEMENTED / API INTEGRATION PENDING', variant: 'warning' },
    body: 'The backend /explain endpoint re-runs the standard pipeline and asks the configured LLM provider for a strictly validated, structured explanation. Explanations are grounded in retrieved techniques — the LLM cannot invent IDs. When the LLM is disabled or unreachable the backend answers 503 LLM_UNAVAILABLE and the frontend shows an honest "AI explanation is currently unavailable" state instead of fabricating content.',
    bullets: [
      'POST /api/v1/explain — grounded structured explanation',
      'Strict output validation (IDs, names, confidence enum)',
      '503 LLM_UNAVAILABLE handled gracefully on the frontend',
      'No fake AI responses are ever displayed',
    ],
  },
  {
    id: 'api-reference',
    title: 'API Reference',
    icon: Network,
    summary:
      'Stable FastAPI contract served at /api/v1 with structured errors and correlation IDs.',
    status: { label: 'VERIFIED', variant: 'success' },
    body: 'The stable contract is documented in API_CONTRACT.md. All application errors use a structured ErrorResponse with a machine-readable error_code. Interactive documentation is available from the backend at /docs.',
    bullets: [
      'GET /api/v1/health — application/model readiness',
      'POST /api/v1/detect — single flow detection',
      'POST /api/v1/detect/batch — multi-flow detection',
      'POST /api/v1/reports/generate — server-side PDF report',
      'Optional X-Correlation-ID header on all requests',
    ],
  },
  {
    id: 'workflow',
    title: 'Detection Workflow',
    icon: Workflow,
    summary:
      'A flow moves through validation, preprocessing, scoring, thresholding, severity and optional intelligence layers.',
    status: { label: 'IMPLEMENTED', variant: 'success' },
    body: 'A network flow is validated, transformed by the frozen pipeline, scored by the Isolation Forest model, compared against the active operating threshold and classified by the placeholder severity calibrator. In the frontend, the Detection page submits real flows to the backend and renders the real response — even when the dashboard and analytics pages are powered by demo data.',
    bullets: [
      'Validate (schema + finite numeric checks)',
      'Preprocess (frozen E2 transformations)',
      'Score (-model.score_samples())',
      'Decide (score >= threshold)',
      'Classify severity and attach retrieval/explanation layers when available',
    ],
  },
  {
    id: 'reports',
    title: 'Report Generation',
    icon: FileText,
    summary:
      'Server-side PDF reports render detection summary, observed indicators, retrieved MITRE context and optional LLM explanation.',
    status: { label: 'BACKEND VERIFIED / FRONTEND INTEGRATION PENDING', variant: 'warning' },
    body: 'The backend generates professional A4 PDF reports from the shared evidence pipeline. Report files live under a controlled directory with server-generated UUID names. The frontend report button posts the analysed flow to /api/v1/reports/generate and exposes the returned download URL for the PDF.',
    bullets: [
      'POST /api/v1/reports/generate → ReportResponse with report_id',
      'GET /api/v1/reports/{report_id}/download → PDF stream',
      'No real PDF is faked on the frontend',
      'Report IDs are strict 32-hex server UUIDs',
    ],
  },
  {
    id: 'demo-data',
    title: 'Demo Data Layer',
    icon: Boxes,
    summary:
      'Pages not yet connected to real analytics endpoints render centralized mock data, clearly labelled as demo.',
    status: { label: 'DEMO', variant: 'info' },
    body: 'Dashboard, Analytics, Documentation, Settings and Help pages read from src/data/mock/ so no fake values are scattered through components. Each module is commented with "MOCK DATA — replace with API integration later" so the swap to real backend responses is a contained change. Detection and Health use the real backend.',
    bullets: [
      'Centralized mock files under src/data/mock/',
      'Typed interfaces with no any',
      'Real detection API preserved on the Detection page',
      'Live health indicator in the header',
    ],
  },
]

// Cross-reference the RAG/LLM/report status wording requested in the docs.
export const integrationStatusLegend: Record<string, string> = {
  IMPLEMENTED: 'Feature is built and usable today.',
  VERIFIED: 'Feature is implemented and covered by the verification suite.',
  'BACKEND VERIFIED / FRONTEND INTEGRATION PENDING':
    'Backend endpoint is verified; the frontend page is still on demo data.',
  'IMPLEMENTED / API INTEGRATION PENDING':
    'Backend endpoint exists; frontend wiring is not yet complete.',
  DEMO: 'Rendered from centralized mock data — not production telemetry.',
}