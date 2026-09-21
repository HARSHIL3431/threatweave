// MOCK DATA — replace with API integration later.
// Settings page: local/demo defaults plus the system configuration block.
// Real values (backend URL, model version, experiment, threshold) are
// overwritten from GET /api/v1/health whenever the backend is reachable.

export const settingsGeneralDefaults = {
  appName: 'AI-Powered Cybersecurity Anomaly Detection',
  environment: 'development',
  themePreference: 'light',
}

export const settingsEnvironmentOptions = [
  { value: 'development', label: 'Development' },
  { value: 'staging', label: 'Staging' },
  { value: 'production', label: 'Production' },
]

export const settingsThemeOptions = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
]

export const settingsDetectionDefaults = {
  operatingPoint: 'OP-A',
  thresholdDisplay: '0.521919',
  detectionMode: 'threshold',
}

export const settingsOperatingPointOptions = [
  { value: 'OP-A', label: 'OP-A (contamination offset)' },
  { value: 'OP-B', label: 'OP-B (validation-optimal)' },
]

export const settingsDetectionModeOptions = [
  { value: 'threshold', label: 'Threshold (OP-A)' },
  { value: 'risk-based', label: 'Risk-based severity' },
]

export const settingsNotificationDefaults = {
  detectionAlerts: true,
  severityAlerts: true,
  reportNotifications: false,
}

// Backend configuration shown in the System section. The backend URL and
// connection status come from the live health check; the rest fall back to
// these demo values when the backend is unreachable.
export const settingsSystemDefaults = {
  backendUrl: 'http://localhost:8001',
  modelVersion: 'isolation_forest_v1',
  experimentId: 'with_port',
  operatingPoint: 'OP-A',
  threshold: 0.521919,
  features: 60,
  dataset: 'CICIDS2017',
}

// Toggles that only persist locally in the browser are labelled with this.
export const localSettingLabel = 'Local / Demo Setting'