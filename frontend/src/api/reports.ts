import apiClient from './client'
import type { NetworkFlowRequest } from './types/detection'
import type { ReportGenerateRequest, ReportResponse, ReportType } from './types/report'

const REPORT_ENDPOINT = '/v1/reports/generate'

/**
 * Generate a server-side PDF report for a network-flow analysis.
 * The backend re-runs the shared ML -> severity -> RAG evidence pipeline,
 * so the report is always derived from the real detection evidence.
 */
export async function generateReport(
  flow: NetworkFlowRequest,
  options: {
    reportType?: ReportType
    appName?: string
    requestId?: string
    topK?: number
  } = {}
): Promise<ReportResponse> {
  const payload: ReportGenerateRequest = {
    report_type: options.reportType ?? 'analysis',
    app_name:
      options.appName ?? 'AI-Powered Cybersecurity Anomaly Detection',
    request_id: options.requestId,
    flow: flow as unknown as Record<string, number>,
    top_k: options.topK ?? 5,
  }

  const response = await apiClient.post<ReportResponse>(REPORT_ENDPOINT, payload)
  return response.data
}