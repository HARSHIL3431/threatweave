export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy'
export type ModelStatus = 'ready' | 'not_loaded' | 'error'

export interface HealthResponse {
  status: HealthStatus
  model_status: ModelStatus
  model_version: string | null
  experiment_id: string | null
  active_operating_point: string | null
  active_threshold: number | null
  timestamp: string
}

// System status for display
export interface SystemStatus {
  isHealthy: boolean
  isModelReady: boolean
  message: string
  lastChecked: string
  details: HealthResponse
}