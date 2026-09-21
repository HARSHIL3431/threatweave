// Shared types for MOCK / DEMO data. These represent the shape of data that
// will later be replaced by the real backend API. See the "MOCK DATA" banner
// comments in this directory before wiring up real endpoints.

import type { LucideIcon } from 'lucide-react'

// Severity levels mirror the backend SeverityLevel contract.
export type MockSeverityLevel = 'info' | 'low' | 'medium' | 'high' | 'critical'

// KPI card shown at the top of the Dashboard.
export interface MockKpiStat {
  id: string
  label: string
  value: string
  description: string
  icon: LucideIcon
  iconClass: string
  trend?: string
  trendClass?: string
}

// Distribution of detections by severity.
export interface MockSeverityDatum {
  level: MockSeverityLevel
  label: string
  count: number
  color: string
}

// A single point on the detection-activity-over-time chart.
export interface MockActivityPoint {
  label: string
  total: number
  anomalous: number
}

// A recent detection event shown in the Dashboard activity table.
export interface MockActivityEvent {
  id: string
  timestamp: string
  requestId: string
  flowId: string
  source: string
  destination: string
  anomalyScore: number
  severity: MockSeverityLevel
  status: 'anomalous' | 'benign'
}

// Traffic volume statistics for the Analytics page.
export interface MockTrafficStat {
  id: string
  label: string
  value: string
  unit: string
  icon: LucideIcon
  iconClass: string
  description: string
}

// Detection patterns ranked by frequency.
export interface MockPatternStat {
  id: string
  name: string
  category: string
  count: number
  score: number
  severity: MockSeverityLevel
}

// Protocol share of analysed traffic.
export interface MockProtocolStat {
  protocol: string
  percentage: number
  color: string
}

// Buckets used by the anomaly-score distribution histogram.
export interface MockScoreBucket {
  range: string
  count: number
}

// A labelled point on an analytics trend line.
export interface MockTrendPoint {
  label: string
  value: number
}

// Documentation page status badge (mirrors <Badge> variants).
export type DocStatusVariant =
  | 'default'
  | 'secondary'
  | 'destructive'
  | 'outline'
  | 'success'
  | 'warning'
  | 'error'
  | 'info'

export interface DocStatus {
  label: string
  variant: DocStatusVariant
}

export interface DocSection {
  id: string
  title: string
  icon: LucideIcon
  summary: string
  status: DocStatus
  body: string
  bullets?: string[]
  code?: string
}

// Help page FAQ entry.
export interface MockFaq {
  question: string
  answer: string
}

// Help page "getting started" step.
export interface MockHelpStep {
  id: string
  title: string
  icon: LucideIcon
  body: string
}