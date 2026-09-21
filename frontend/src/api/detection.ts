import apiClient from './client'
import type {
  NetworkFlowRequest,
  DetectionResponse,
  BatchDetectionRequest,
  BatchDetectionResponse,
  ApiError,
} from './types/detection'

const DETECTION_ENDPOINTS = {
  SINGLE: '/v1/detect',
  BATCH: '/v1/detect/batch',
} as const

/**
 * Submit a single network flow for anomaly detection
 */
export async function detectFlow(
  flow: NetworkFlowRequest
): Promise<DetectionResponse> {
  try {
    const response = await apiClient.post<DetectionResponse>(
      DETECTION_ENDPOINTS.SINGLE,
      flow
    )
    return response.data
  } catch (error) {
    throw handleDetectionError(error)
  }
}

/**
 * Submit multiple network flows for batch detection
 */
export async function detectBatch(
  flows: NetworkFlowRequest[]
): Promise<BatchDetectionResponse> {
  try {
    const request: BatchDetectionRequest = { flows }
    const response = await apiClient.post<BatchDetectionResponse>(
      DETECTION_ENDPOINTS.BATCH,
      request
    )
    return response.data
  } catch (error) {
    throw handleDetectionError(error)
  }
}

/**
 * Validate a network flow without submitting for detection
 * This is a client-side validation helper
 */
export function validateFlow(flow: NetworkFlowRequest): string[] {
  const errors: string[] = []

  // Check required numeric fields
  const requiredFields: (keyof NetworkFlowRequest)[] = [
    'Destination Port',
    'Flow Duration',
    'Total Fwd Packets',
    'Total Backward Packets',
  ]

  for (const field of requiredFields) {
    const value = flow[field]
    if (value === undefined || value === null) {
      errors.push(`${field} is required`)
    } else if (typeof value !== 'number') {
      errors.push(`${field} must be a number`)
    } else if (!Number.isFinite(value)) {
      errors.push(`${field} must be a finite number`)
    }
  }

  // Check for NaN and Infinity in all numeric fields
  Object.entries(flow).forEach(([field, value]) => {
    if (typeof value === 'number') {
      if (Number.isNaN(value)) {
        errors.push(`${field} cannot be NaN`)
      }
      if (!Number.isFinite(value)) {
        errors.push(`${field} cannot be Infinity`)
      }
    }
  })

  return errors
}

/**
 * Format a detection response for display
 */
export function formatDetectionResult(result: DetectionResponse) {
  const { detection, severity, metadata } = result
  
  return {
    isAnomalous: detection.is_anomaly,
    score: detection.anomaly_score,
    threshold: detection.threshold,
    severity: severity.level,
    riskScore: severity.risk_score,
    modelVersion: metadata.model_version,
    experimentId: detection.experiment_id,
    operatingPoint: detection.operating_point,
    timestamp: metadata.timestamp,
  }
}

/**
 * Calculate score percentage for visualization
 */
export function calculateScorePercentage(score: number, _threshold: number): number {
  // Normalize score to percentage (0-100) with threshold as reference point
  // Scores below threshold show as lower percentage, above as higher
  const normalized = Math.min(Math.max(score * 100, 0), 100)
  return normalized
}

/**
 * Get severity color based on level
 */
export function getSeverityColor(level: string): string {
  switch (level) {
    case 'critical':
      return 'severity-critical'
    case 'high':
      return 'severity-high'
    case 'medium':
      return 'severity-medium'
    case 'low':
      return 'severity-low'
    case 'info':
      return 'severity-info'
    default:
      return 'gray-500'
  }
}

/**
 * Error handling helper for detection API calls
 */
function handleDetectionError(error: unknown): ApiError {
  if (typeof error === 'object' && error !== null && 'code' in error) {
    return error as ApiError
  }
  
  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unknown error occurred during detection',
    original: error,
  }
}