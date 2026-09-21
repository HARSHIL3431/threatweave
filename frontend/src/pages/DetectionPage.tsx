import { useState } from 'react'
import {
  BrainCircuit,
  Download,
  FileText,
  FileDown,
  Search,
  Shield,
  Upload,
  BarChart3,
  Loader2,
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Alert } from '@/components/ui/Alert'
import PageHeader from '@/components/ui/PageHeader'
import ScrollReveal from '@/components/animations/ScrollReveal'
import FlowInput from '@/features/detection/FlowInput'
import ResultDisplay from '@/features/detection/ResultDisplay'
import { useSystemHealth } from '@/hooks/useHealth'
import { generateReport } from '@/api/reports'
import { explainFlow } from '@/api/explain'
import type { DetectionResponse } from '@/api/types/detection'
import type { NetworkFlowRequest } from '@/api/types/detection'
import type { ReportResponse } from '@/api/types/report'
import type { FieldExplanation } from '@/api/types/explain'

type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; message: string }

const DetectionPage = () => {
  const [detectionResult, setDetectionResult] = useState<DetectionResponse | null>(null)
  const [lastFlow, setLastFlow] = useState<NetworkFlowRequest | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const [reportState, setReportState] = useState<AsyncState<ReportResponse>>({ status: 'idle' })
  const [explainState, setExplainState] = useState<AsyncState<FieldExplanation>>({ status: 'idle' })

  const { data: systemHealth, isLoading: healthLoading } = useSystemHealth()
  const backendUnavailable = systemHealth !== undefined && !systemHealth.isHealthy

  const handleDetectionComplete = (result: DetectionResponse, flow: NetworkFlowRequest) => {
    setDetectionResult(result)
    setLastFlow(flow)
    setReportState({ status: 'idle' })
    setExplainState({ status: 'idle' })
  }

  const getErrorMessage = (err: unknown): string => {
    if (typeof err === 'object' && err !== null && 'code' in err) {
      const code = (err as { code: string }).code
      if (code === 'LLM_UNAVAILABLE') {
        return 'AI explanation is currently unavailable.'
      }
      if (code === 'NETWORK_ERROR') {
        return 'Could not reach the backend. Check that the service is running.'
      }
      return (err as { message?: string }).message || 'An unexpected error occurred.'
    }
    return 'An unexpected error occurred.'
  }

  const handleGenerateReport = async () => {
    if (!lastFlow || !detectionResult) return
    setReportState({ status: 'loading' })
    try {
      const report = await generateReport(lastFlow, {
        requestId: detectionResult.request_id,
      })
      setReportState({ status: 'success', data: report })
      toast.success('Report generated')
    } catch (err) {
      const message = getErrorMessage(err)
      setReportState({ status: 'error', message })
      toast.error(message)
    }
  }

  const handleExplain = async () => {
    if (!lastFlow) return
    setExplainState({ status: 'loading' })
    try {
      const response = await explainFlow(lastFlow)
      setExplainState({ status: 'success', data: response.explanation })
    } catch (err) {
      const message = getErrorMessage(err)
      setExplainState({ status: 'error', message })
    }
  }

  const mitreTechniques = detectionResult?.attack_context.mitre_techniques ?? []
  const retrievedContext = detectionResult?.attack_context.retrieved_context ?? []

  return (
    <div className="space-y-8">
      {/* Header */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <PageHeader
          title="Network Flow Detection"
          description="Submit network flows for anomaly detection using the frozen E2 Isolation Forest model"
          right={
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Upload className="h-4 w-4" />
              <span>
                {healthLoading
                  ? 'Checking backend…'
                  : backendUnavailable
                    ? 'Backend unavailable'
                    : 'Real backend detection'}
              </span>
            </div>
          }
        />
      </ScrollReveal>

      {backendUnavailable && (
        <ScrollReveal direction="up" distance={20} duration={0.6}>
          <Alert variant="warning" title="Backend unreachable">
            Detection requires the FastAPI backend (expected on localhost:8001). The page will show
            the real error state until the backend is available — it never substitutes mock results.
          </Alert>
        </ScrollReveal>
      )}

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Section */}
        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Flow Input
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FlowInput
                onDetectionComplete={handleDetectionComplete}
                isLoading={isLoading}
                setIsLoading={setIsLoading}
              />
            </CardContent>
          </Card>
        </ScrollReveal>

        {/* Result Section */}
        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.2}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Detection Result
              </CardTitle>
            </CardHeader>
            <CardContent>
              {detectionResult ? (
                <ResultDisplay result={detectionResult} />
              ) : (
                <div className="text-center py-12">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
                    <BarChart3 className="h-8 w-8 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-medium mb-2">No Detection Yet</h3>
                  <p className="text-gray-500 mb-6">
                    Submit a network flow to see the anomaly detection results here.
                  </p>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>• Anomaly score vs threshold visualization</p>
                    <p>• Severity classification</p>
                    <p>• Model information</p>
                    <p>• Report generation and AI explanation</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </ScrollReveal>
      </div>

      {/* Intelligence Layers & Report */}
      {detectionResult && lastFlow && (
        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.2}>
          <Card className="hover:shadow-lg transition-shadow duration-300">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Intelligence Layers & Reports
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* MITRE ATT&CK */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium flex items-center gap-2">
                    <Search className="h-4 w-4" /> MITRE ATT&CK
                  </h4>
                  <Badge variant="success" size="sm">Backend Verified</Badge>
                </div>
                {retrievedContext.length > 0 ? (
                  <div className="space-y-2">
                    {retrievedContext.map((item, index) => (
                      <div key={index} className="p-3 rounded-lg bg-gray-50 text-sm">
                        <span className="font-medium">{item}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Alert variant="info">
                    <p className="text-sm">
                      Contextual threat intelligence will appear here after analysis. The backend
                      returns retrieved-not-confirmed ATT&CK candidates only when the RAG index is
                      loaded.
                    </p>
                  </Alert>
                )}
                {mitreTechniques.length === 0 && retrievedContext.length === 0 && (
                  <p className="text-xs text-gray-500">
                    Detection returned no retrieved context for this flow.
                  </p>
                )}
              </div>

              {/* LLM Explanation */}
              <div className="space-y-3 border-t pt-6">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium flex items-center gap-2">
                    <BrainCircuit className="h-4 w-4" /> LLM Explanation
                  </h4>
                  <Badge variant="warning" size="sm">Integration Pending</Badge>
                </div>

                {explainState.status === 'idle' && (
                  <div>
                    <p className="text-sm text-gray-600 mb-3">
                      Request a grounded explanation for this flow. The backend only answers when
                      the LLM provider is configured — it will never return fabricated content.
                    </p>
                    <Button onClick={handleExplain} className="gap-2">
                      <BrainCircuit className="h-4 w-4" />
                      Explain Analysis
                    </Button>
                  </div>
                )}

                {explainState.status === 'loading' && (
                  <Alert variant="info">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generating grounded explanation…
                    </div>
                  </Alert>
                )}

                {explainState.status === 'error' && (
                  <Alert variant="destructive" title="AI explanation currently unavailable">
                    <p className="text-sm">{explainState.message}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3"
                      onClick={handleExplain}
                    >
                      Retry
                    </Button>
                  </Alert>
                )}

                {explainState.status === 'success' && (
                  <div className="space-y-4">
                    <Alert variant="success">
                      <p className="text-sm font-medium">{explainState.data.summary}</p>
                    </Alert>
                    <div className="p-4 rounded-lg bg-gray-50 space-y-2">
                      <p className="text-sm text-gray-700">{explainState.data.anomaly_assessment}</p>
                      {explainState.data.observed_indicators.length > 0 && (
                        <ul className="space-y-1 text-sm text-gray-600">
                          {explainState.data.observed_indicators.map((ind, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-primary-600">•</span>
                              <span>{ind}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                    {explainState.data.recommended_actions.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Recommended actions</p>
                        <ul className="space-y-1 text-sm text-gray-600">
                          {explainState.data.recommended_actions.map((action, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-green-600">•</span>
                              <span>{action}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {explainState.data.limitations.length > 0 && (
                      <p className="text-xs text-gray-500">
                        {explainState.data.limitations.join(' ')}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Report Generation */}
              <div className="space-y-3 border-t pt-6">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium flex items-center gap-2">
                    <FileDown className="h-4 w-4" /> PDF Report
                  </h4>
                  <Badge variant="success" size="sm">Backend Verified</Badge>
                </div>

                {reportState.status === 'idle' && (
                  <Button onClick={handleGenerateReport} className="gap-2">
                    <FileText className="h-4 w-4" />
                    Generate PDF Report
                  </Button>
                )}

                {reportState.status === 'loading' && (
                  <Alert variant="info">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      The backend is rendering this flow's evidence into a PDF…
                    </div>
                  </Alert>
                )}

                {reportState.status === 'error' && (
                  <Alert variant="destructive" title="Report generation failed">
                    <p className="text-sm">{reportState.message}</p>
                  </Alert>
                )}

                {reportState.status === 'success' && (
                  <div className="space-y-3">
                    <Alert variant="success" title="Report ready">
                      <p className="text-sm">
                        The PDF was generated from the real detection evidence ({formatBytes(reportState.data.size_bytes)}).
                      </p>
                    </Alert>
                    <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-gray-50">
                      <div className="min-w-0">
                        <p className="text-sm font-mono truncate">{reportState.data.file_name}</p>
                        <p className="text-xs text-gray-500">
                          Report ID: {reportState.data.report_id.slice(0, 8)}…
                        </p>
                      </div>
                      <a
                        href={reportState.data.download_url}
                        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors"
                      >
                        <Download className="h-4 w-4" />
                        Download PDF
                      </a>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>
      )}

      {/* Information Section */}
      <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.3}>
        <Card className="hover:shadow-lg transition-shadow duration-300">
          <CardHeader>
            <CardTitle>Detection Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="font-medium text-lg">Current Configuration</h4>
                <div className="space-y-3">
                  <div className="flex justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">Active Model:</span>
                    <span className="font-medium">E2 Isolation Forest</span>
                  </div>
                  <div className="flex justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">Operating Point:</span>
                    <span className="font-medium">OP-A (0.5219)</span>
                  </div>
                  <div className="flex justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">Features:</span>
                    <span className="font-medium">60 CICIDS2017 features</span>
                  </div>
                  <div className="flex justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">Preprocessing:</span>
                    <span className="font-medium">Frozen E2 pipeline</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium text-lg">How Detection Works</h4>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-6 h-6 rounded-full bg-primary-500 text-white flex items-center justify-center text-xs mt-0.5 flex-shrink-0">
                      1
                    </div>
                    <span className="text-gray-700">Network flows are validated against the 60-feature E2 schema</span>
                  </li>
                  <li className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-6 h-6 rounded-full bg-primary-500 text-white flex items-center justify-center text-xs mt-0.5 flex-shrink-0">
                      2
                    </div>
                    <span className="text-gray-700">Preprocessing matches the frozen training pipeline exactly</span>
                  </li>
                  <li className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-6 h-6 rounded-full bg-primary-500 text-white flex items-center justify-center text-xs mt-0.5 flex-shrink-0">
                      3
                    </div>
                    <span className="text-gray-700">Isolation Forest computes anomaly scores (-model.score_samples())</span>
                  </li>
                  <li className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-6 h-6 rounded-full bg-primary-500 text-white flex items-center justify-center text-xs mt-0.5 flex-shrink-0">
                      4
                    </div>
                    <span className="text-gray-700">Scores are compared to the frozen OP-A threshold (0.5219)</span>
                  </li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </ScrollReveal>
    </div>
  )
}

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default DetectionPage