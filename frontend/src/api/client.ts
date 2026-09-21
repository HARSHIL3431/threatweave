import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for detection requests
})

// Request interceptor for adding correlation IDs
apiClient.interceptors.request.use(
  (config) => {
    // Add correlation ID if not present
    if (!config.headers['X-Correlation-ID']) {
      config.headers['X-Correlation-ID'] = `frontend-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle network errors
    if (!error.response) {
      return Promise.reject({
        code: 'NETWORK_ERROR',
        message: 'Network error. Please check your connection.',
        original: error,
      })
    }

    // Handle backend errors with structured error response
    const backendError = error.response.data
    if (backendError && backendError.error_code) {
      return Promise.reject({
        code: backendError.error_code,
        message: backendError.message || 'An error occurred',
        details: backendError.details || {},
        timestamp: backendError.timestamp,
        requestId: backendError.request_id,
      })
    }

    // Handle generic HTTP errors
    return Promise.reject({
      code: `HTTP_${error.response.status}`,
      message: `Request failed with status ${error.response.status}`,
      status: error.response.status,
      original: error,
    })
  }
)

export default apiClient