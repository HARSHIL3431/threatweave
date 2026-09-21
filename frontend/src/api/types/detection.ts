// Network flow input - 60 features from E2 experiment
export interface NetworkFlowRequest {
  'Destination Port': number
  'Flow Duration': number
  'Total Fwd Packets': number
  'Total Backward Packets': number
  'Total Length of Fwd Packets': number
  'Total Length of Bwd Packets': number
  'Fwd Packet Length Max': number
  'Fwd Packet Length Min': number
  'Fwd Packet Length Mean': number
  'Fwd Packet Length Std': number
  'Bwd Packet Length Max': number
  'Bwd Packet Length Min': number
  'Bwd Packet Length Mean': number
  'Bwd Packet Length Std': number
  'Flow Bytes/s': number
  'Flow Packets/s': number
  'Flow IAT Mean': number
  'Flow IAT Std': number
  'Flow IAT Max': number
  'Flow IAT Min': number
  'Fwd IAT Total': number
  'Fwd IAT Mean': number
  'Fwd IAT Std': number
  'Fwd IAT Max': number
  'Fwd IAT Min': number
  'Bwd IAT Total': number
  'Bwd IAT Mean': number
  'Bwd IAT Std': number
  'Bwd IAT Max': number
  'Bwd IAT Min': number
  'Fwd PSH Flags': number
  'Fwd URG Flags': number
  'Fwd Header Length': number
  'Fwd Packets/s': number
  'Bwd Packets/s': number
  'Min Packet Length': number
  'Max Packet Length': number
  'Packet Length Mean': number
  'Packet Length Std': number
  'Packet Length Variance': number
  'FIN Flag Count': number
  'RST Flag Count': number
  'PSH Flag Count': number
  'ACK Flag Count': number
  'URG Flag Count': number
  'Down/Up Ratio': number
  'Average Packet Size': number
  'Init_Win_bytes_forward': number
  'Init_Win_bytes_backward': number
  'act_data_pkt_fwd': number
  'min_seg_size_forward': number
  'Active Mean': number
  'Active Std': number
  'Active Max': number
  'Active Min': number
  'Idle Mean': number
  'Idle Std': number
  'Idle Max': number
  'Idle Min': number
  'Is_Zero_Duration'?: number // Optional, computed by backend
}

export interface DetectionDetails {
  is_anomaly: boolean
  anomaly_score: number
  threshold: number
  experiment_id: string
  operating_point: string
}

export type SeverityLevel = 'info' | 'low' | 'medium' | 'high' | 'critical'

export interface SeverityDetails {
  level: SeverityLevel
  risk_score: number
  calibration_note: string
}

export interface AttackContext {
  mitre_techniques: string[]
  retrieved_context: string[]
}

export interface Explanation {
  summary: string | null
  reasoning: string | null
  recommendations: string[]
}

export interface Metadata {
  model_version: string
  source_dataset: string
  timestamp: string
}

export interface DetectionResponse {
  request_id: string
  detection: DetectionDetails
  severity: SeverityDetails
  attack_context: AttackContext
  explanation: Explanation
  metadata: Metadata
}

export interface BatchDetectionRequest {
  flows: NetworkFlowRequest[]
}

export interface BatchDetectionResponse {
  batch_id: string
  count: number
  results: DetectionResponse[]
  timestamp: string
}

// Sample flow data from fixtures
export interface SampleFlow {
  id: string
  name: string
  description: string
  data: NetworkFlowRequest
  expectedScore?: number
  expectedIsAnomaly?: boolean
}

// Simplified flow for form display
export interface SimplifiedFlow {
  destinationPort: number
  flowDuration: number
  totalFwdPackets: number
  totalBackwardPackets: number
  totalLengthFwd: number
  totalLengthBwd: number
  flowBytesPerS: number
  flowPacketsPerS: number
}

// API error response
export interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
  timestamp?: string
  requestId?: string
  status?: number
  original?: unknown
}