// MOCK DATA — replace with API integration later.
// Help page: getting-started steps, FAQ content and a support placeholder.
// No fabricated contact information is included.

import { AlertTriangle, FileText, Scale, Search, Upload, BrainCircuit } from 'lucide-react'
import type { MockFaq, MockHelpStep } from './types'

export const gettingStartedSteps: MockHelpStep[] = [
  {
    id: 'submit-flow',
    title: 'Submit a Network Flow',
    icon: Upload,
    body: 'Open the Detection page, pick a sample flow or enter flow parameters manually, then run the analysis. The flow is validated and scored by the real backend when it is reachable.',
  },
  {
    id: 'anomaly-score',
    title: 'Interpret the Anomaly Score',
    icon: Scale,
    body: 'The anomaly score is computed as -model.score_samples(). Higher scores are more anomalous. The flow is flagged when the score is at or above the active operating threshold.',
  },
  {
    id: 'severity',
    title: 'Understand Severity',
    icon: AlertTriangle,
    body: 'Severity levels run from info to critical and are calibrated from the anomaly score and risk score. Severity is placeholder-calibrated until the calibration service is finalised.',
  },
  {
    id: 'mitre-context',
    title: 'How MITRE Context Works',
    icon: Search,
    body: 'When enabled, the backend retrieves candidate MITRE ATT&CK techniques related to the flow. These are "retrieved-not-confirmed" candidates for context, never confirmed attacks.',
  },
  {
    id: 'ai-explanation',
    title: 'Describe AI Explanations',
    icon: BrainCircuit,
    body: 'The LLM endpoint generates grounded explanations with recommended actions. Explanations are generative and explanatory. When unavailable, the UI says so honestly rather than faking content.',
  },
  {
    id: 'reports',
    title: 'Generate Reports',
    icon: FileText,
    body: 'After an analysis, the report button asks the backend to generate a PDF that summarises the detection evidence. Reports are stored server-side and downloaded through a secure URL.',
  },
]

export const faqs: MockFaq[] = [
  {
    question: 'What does anomaly score mean?',
    answer:
      'Anomaly score is computed as -model.score_samples() from the Isolation Forest model. A higher score means the flow looks more unusual relative to the training distribution. A flow is flagged anomalous when its score is greater than or equal to the active operating threshold (OP-A = 0.521919 in the frozen model).',
  },
  {
    question: 'What does medium severity mean?',
    answer:
      'Severity is a risk-oriented label derived from the anomaly score and risk score. Medium indicates the flow was flagged as anomalous but the current placeholder calibration does not rank it as high or critical. Severity calibration is labelled "initial placeholder" until the calibration service is finalised.',
  },
  {
    question: 'What does retrieved-not-confirmed mean?',
    answer:
      'When RAG is enabled, the backend retrieves MITRE ATT&CK techniques that are contextually relevant to the flow. "Retrieved-not-confirmed" means those techniques are candidates for investigation only — they are not confirmed detections or attribution for the flow.',
  },
  {
    question: 'Why is AI explanation unavailable?',
    answer:
      'The LLM explanation layer runs on the backend /explain endpoint and only answers when LLM_ENABLED is true and an API key is configured. When the backend answers 503 LLM_UNAVAILABLE, the frontend displays "AI explanation is currently unavailable" — it never fabricates an explanation.',
  },
  {
    question: 'How do I generate a report?',
    answer:
      'Run a detection first, then use the report action on the Detection page. The frontend posts the analysed flow to POST /api/v1/reports/generate and the backend returns a report_id plus a download URL for the rendered PDF.',
  },
  {
    question: 'Where are reports stored?',
    answer:
      'Reports are generated and stored server-side inside the configured reports directory (data/reports by default). Each file uses a server-generated UUID name; nothing user-supplied is ever used as a path.',
  },
]

export const supportPlaceholder = {
  title: 'Contact Support',
  note: 'Support contact details are not configured for this development build. Use the project repository, API contract documentation and the Documentation page for answers.',
}