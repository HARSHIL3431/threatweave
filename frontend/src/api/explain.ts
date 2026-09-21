import apiClient from './client'
import type { NetworkFlowRequest } from './types/detection'
import type { ExplainResponse } from './types/explain'

const EXPLAIN_ENDPOINT = '/v1/explain'

/**
 * Request a grounded structured LLM explanation for a network flow.
 * The backend re-runs the standard ML -> severity -> RAG pipeline and only
 * then asks the configured LLM provider for a validated explanation.
 * Returns HTTP 503 LLM_UNAVAILABLE when the LLM is disabled or unconfigured.
 */
export async function explainFlow(
  flow: NetworkFlowRequest,
  topK = 5
): Promise<ExplainResponse> {
  const response = await apiClient.post<ExplainResponse>(EXPLAIN_ENDPOINT, {
    flow,
    top_k: topK,
  })
  return response.data
}