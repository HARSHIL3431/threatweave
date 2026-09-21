// MOCK DATA — replace with API integration later.
// Analytics page: detection trends, severity/score distributions, top patterns,
// protocol share and traffic statistics. All values are illustrative demo data.

import { BarChart3, Cpu, Globe2, Network, Radio } from 'lucide-react'
import type {
  MockPatternStat,
  MockProtocolStat,
  MockScoreBucket,
  MockSeverityDatum,
  MockTrafficStat,
  MockTrendPoint,
} from './types'

// Time ranges the UI can filter on. Operates on mock data only for now.
export const analyticsTimeRanges = ['Last 24h', 'Last 7 days', 'Last 30 days'] as const

export const detectionTrends: MockTrendPoint[] = [
  { label: 'Mon', value: 92 },
  { label: 'Tue', value: 118 },
  { label: 'Wed', value: 104 },
  { label: 'Thu', value: 137 },
  { label: 'Fri', value: 126 },
  { label: 'Sat', value: 88 },
  { label: 'Sun', value: 79 },
]

export const analyticsSeverityDistribution: MockSeverityDatum[] = [
  { level: 'critical', label: 'Critical', count: 41, color: '#dc2626' },
  { level: 'high', label: 'High', count: 87, color: '#ef4444' },
  { level: 'medium', label: 'Medium', count: 123, color: '#f59e0b' },
  { level: 'low', label: 'Low', count: 135, color: '#10b981' },
]

export const anomalyScoreDistribution: MockScoreBucket[] = [
  { range: '0.0–0.2', count: 1620 },
  { range: '0.2–0.4', count: 481 },
  { range: '0.4–0.5', count: 360 },
  { range: '0.5–0.6', count: 214 },
  { range: '0.6–0.7', count: 96 },
  { range: '0.7–0.8', count: 51 },
  { range: '0.8–0.9', count: 21 },
  { range: '0.9–1.0', count: 4 },
]

export const topPatterns: MockPatternStat[] = [
  {
    id: 't-1',
    name: 'Port Scan (vertical sweep)',
    category: 'Reconnaissance',
    count: 118,
    score: 0.92,
    severity: 'critical',
  },
  {
    id: 't-2',
    name: 'DoS / Heartbleed attempt',
    category: 'DoS',
    count: 87,
    score: 0.88,
    severity: 'high',
  },
  {
    id: 't-3',
    name: 'Web attack — brute force',
    category: 'Web Attack',
    count: 64,
    score: 0.84,
    severity: 'high',
  },
  {
    id: 't-4',
    name: 'SSH credential stuffing',
    category: 'Brute Force',
    count: 49,
    score: 0.79,
    severity: 'medium',
  },
  {
    id: 't-5',
    name: 'Botnet C2 beaconing',
    category: 'Botnet',
    count: 36,
    score: 0.91,
    severity: 'critical',
  },
  {
    id: 't-6',
    name: 'Infiltration anomaly',
    category: 'Infiltration',
    count: 21,
    score: 0.74,
    severity: 'medium',
  },
]

export const protocolDistribution: MockProtocolStat[] = [
  { protocol: 'TCP', percentage: 68, color: '#2563eb' },
  { protocol: 'UDP', percentage: 22, color: '#8b5cf6' },
  { protocol: 'ICMP', percentage: 7, color: '#f59e0b' },
  { protocol: 'Other', percentage: 3, color: '#64748b' },
]

export const trafficStats: MockTrafficStat[] = [
  {
    id: 'tx-rate',
    label: 'Average Throughput',
    value: '2.4',
    unit: 'flows/s',
    icon: Radio,
    iconClass: 'bg-blue-100 text-blue-600',
    description: 'Mean analysis rate across the period',
  },
  {
    id: 'active-ips',
    label: 'Active Hosts',
    value: '1,208',
    unit: 'IPs',
    icon: Globe2,
    iconClass: 'bg-purple-100 text-purple-600',
    description: 'Unique source IPs observed',
  },
  {
    id: 'sessions',
    label: 'Sessions',
    value: '39,412',
    unit: 'flows',
    icon: Network,
    iconClass: 'bg-green-100 text-green-600',
    description: 'Total flows analysed this period',
  },
  {
    id: 'models',
    label: 'Inference Load',
    value: '68',
    unit: '% CPU',
    icon: Cpu,
    iconClass: 'bg-orange-100 text-orange-600',
    description: 'Estimated model inference utilisation',
  },
  {
    id: 'flagged',
    label: 'Flagged Flows',
    value: '386',
    unit: 'events',
    icon: BarChart3,
    iconClass: 'bg-red-100 text-red-600',
    description: 'Flows above the operating threshold',
  },
]

// Mock summary numbers reported under "Traffic Statistics".
export const trafficSummary = {
  benignSharePercentage: 86.45,
  anomalousSharePercentage: 13.55,
  highRiskSharePercentage: 3.85,
  avgScore: 0.31,
}