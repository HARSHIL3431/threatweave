import apiClient from './client'
import type { HealthResponse, SystemStatus } from './types/health'

const HEALTH_ENDPOINT = '/v1/health'

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await apiClient.get<HealthResponse>(HEALTH_ENDPOINT)
    return response.data
  } catch (error) {
    // If health endpoint fails, return degraded status
    return {
      status: 'unhealthy',
      model_status: 'error',
      model_version: null,
      experiment_id: null,
      active_operating_point: null,
      active_threshold: null,
      timestamp: new Date().toISOString(),
    }
  }
}

/**
 * Get formatted system status for display
 */
export async function getSystemStatus(): Promise<SystemStatus> {
  const health = await checkHealth()
  
  const isHealthy = health.status === 'healthy'
  const isModelReady = health.model_status === 'ready'
  
  let message = 'System is operational'
  if (!isHealthy) {
    message = 'Backend service is unavailable'
  } else if (!isModelReady) {
    message = 'Model is not ready for detection'
  }
  
  return {
    isHealthy,
    isModelReady,
    message,
    lastChecked: health.timestamp,
    details: health,
  }
}

/**
 * Format health response for display
 */
export function formatHealthResponse(health: HealthResponse) {
  return {
    status: health.status,
    modelStatus: health.model_status,
    modelVersion: health.model_version || 'Unknown',
    experimentId: health.experiment_id || 'Unknown',
    operatingPoint: health.active_operating_point || 'Unknown',
    threshold: health.active_threshold || 0,
    timestamp: health.timestamp,
  }
}

/**
 * Get status color based on health status
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'healthy':
      return 'green-500'
    case 'degraded':
      return 'yellow-500'
    case 'unhealthy':
      return 'red-500'
    default:
      return 'gray-500'
  }
}

/**
 * Get model status color
 */
export function getModelStatusColor(status: string): string {
  switch (status) {
    case 'ready':
      return 'green-500'
    case 'not_loaded':
      return 'yellow-500'
    case 'error':
      return 'red-500'
    default:
      return 'gray-500'
  }
}