// Types matching the backend /explain contract (app/schemas/llm.py).
import type { DetectionDetails, SeverityDetails, AttackContext } from './detection'

export interface PotentialAttackContext {
  technique_id: string
  technique_name: string
  confidence: string
  reason: string
}

export interface FieldExplanation {
  summary: string
  anomaly_assessment: string
  observed_indicators: string[]
  potential_attack_context: PotentialAttackContext[]
  recommended_actions: string[]
  limitations: string[]
}

export interface LlmMetadata {
  provider: string
  model: string
  latency_ms: number
  validated: boolean
}

export interface ExplainResponse {
  request_id: string
  detection: DetectionDetails
  severity: SeverityDetails
  attack_context: AttackContext
  explanation: FieldExplanation
  llm: LlmMetadata
}