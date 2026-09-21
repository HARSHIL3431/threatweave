// MOCK DATA — replace with API integration later.
// Dashboard KPIs, activity series, severity distribution and recent events.
// Every value here is illustrative demo data, not production telemetry.

import { Activity, AlertTriangle, Gauge, Percent } from 'lucide-react'
import type {
  MockActivityEvent,
  MockActivityPoint,
  MockKpiStat,
  MockSeverityDatum,
} from './types'

export const dashboardKpis: MockKpiStat[] = [
  {
    id: 'total-analyses',
    label: 'Total Analyses',
    value: '2,847',
    description: 'Network flows analysed this period',
    icon: Activity,
    iconClass: 'bg-blue-100 text-blue-600',
    trend: '+12.4%',
    trendClass: 'text-green-600',
  },
  {
    id: 'anomalies',
    label: 'Anomalies Detected',
    value: '386',
    description: 'Flows flagged above the OP-A threshold',
    icon: AlertTriangle,
    iconClass: 'bg-red-100 text-red-600',
    trend: '+3.1%',
    trendClass: 'text-red-600',
  },
  {
    id: 'detection-rate',
    label: 'Detection Rate',
    value: '13.55%',
    description: 'Anomalous share of all analysed flows',
    icon: Percent,
    iconClass: 'bg-purple-100 text-purple-600',
    trend: '−0.8%',
    trendClass: 'text-green-600',
  },
  {
    id: 'avg-risk',
    label: 'Average Risk Score',
    value: '0.68',
    description: 'Mean risk score across flagged flows',
    icon: Gauge,
    iconClass: 'bg-orange-100 text-orange-600',
    trend: '+0.02',
    trendClass: 'text-red-600',
  },
]

// NOTE: the fifth KPI ("System Status") is intentionally NOT mocked here.
// It maps to the live backend health check (src/hooks/useHealth.ts).

export const detectionActivity: MockActivityPoint[] = [
  { label: 'Sep 21', total: 61, anomalous: 9 },
  { label: 'Sep 22', total: 74, anomalous: 11 },
  { label: 'Sep 23', total: 68, anomalous: 8 },
  { label: 'Sep 24', total: 92, anomalous: 14 },
  { label: 'Sep 25', total: 85, anomalous: 12 },
  { label: 'Sep 26', total: 103, anomalous: 16 },
  { label: 'Sep 27', total: 96, anomalous: 13 },
  { label: 'Sep 28', total: 118, anomalous: 17 },
  { label: 'Sep 29', total: 110, anomalous: 15 },
  { label: 'Sep 30', total: 132, anomalous: 19 },
  { label: 'Oct 01', total: 127, anomalous: 18 },
  { label: 'Oct 02', total: 140, anomalous: 21 },
  { label: 'Oct 03', total: 150, anomalous: 22 },
  { label: 'Oct 04', total: 145, anomalous: 20 },
  { label: 'Oct 05', total: 161, anomalous: 24 },
  { label: 'Oct 06', total: 158, anomalous: 23 },
  { label: 'Oct 07', total: 172, anomalous: 26 },
  { label: 'Oct 08', total: 169, anomalous: 25 },
  { label: 'Oct 09', total: 181, anomalous: 27 },
  { label: 'Oct 10', total: 178, anomalous: 26 },
  { label: 'Oct 11', total: 193, anomalous: 29 },
  { label: 'Oct 12', total: 187, anomalous: 28 },
  { label: 'Oct 13', total: 202, anomalous: 31 },
  { label: 'Oct 14', total: 199, anomalous: 30 },
  { label: 'Oct 15', total: 214, anomalous: 33 },
  { label: 'Oct 16', total: 208, anomalous: 32 },
  { label: 'Oct 17', total: 226, anomalous: 35 },
  { label: 'Oct 18', total: 221, anomalous: 34 },
  { label: 'Oct 19', total: 238, anomalous: 37 },
  { label: 'Oct 20', total: 233, anomalous: 36 },
]

// Sum of the severity counts below equals the "Anomalies Detected" KPI.
export const severityDistribution: MockSeverityDatum[] = [
  { level: 'critical', label: 'Critical', count: 41, color: '#dc2626' },
  { level: 'high', label: 'High', count: 87, color: '#ef4444' },
  { level: 'medium', label: 'Medium', count: 123, color: '#f59e0b' },
  { level: 'low', label: 'Low', count: 135, color: '#10b981' },
]

export const recentActivity: MockActivityEvent[] = [
  {
    id: 'evt-001',
    timestamp: '2026-10-20T09:42:11Z',
    requestId: 'req-8f3a1c',
    flowId: 'flow-011284',
    source: '10.0.31.7',
    destination: '10.0.12.40:443',
    anomalyScore: 0.8941,
    severity: 'critical',
    status: 'anomalous',
  },
  {
    id: 'evt-002',
    timestamp: '2026-10-20T09:40:03Z',
    requestId: 'req-7d2b9f',
    flowId: 'flow-011283',
    source: '172.16.84.22',
    destination: '10.0.4.11:22',
    anomalyScore: 0.7612,
    severity: 'high',
    status: 'anomalous',
  },
  {
    id: 'evt-003',
    timestamp: '2026-10-20T09:37:49Z',
    requestId: 'req-6c9a2e',
    flowId: 'flow-011282',
    source: '192.168.44.9',
    destination: '10.0.8.33:49188',
    anomalyScore: 0.3120,
    severity: 'low',
    status: 'benign',
  },
  {
    id: 'evt-004',
    timestamp: '2026-10-20T09:35:28Z',
    requestId: 'req-5b88fcf',
    flowId: 'flow-011281',
    source: '10.0.22.61',
    destination: '10.0.9.7:8080',
    anomalyScore: 0.5834,
    severity: 'medium',
    status: 'anomalous',
  },
  {
    id: 'evt-005',
    timestamp: '2026-10-20T09:33:15Z',
    requestId: 'req-4a7cce',
    flowId: 'flow-011280',
    source: '203.0.113.45',
    destination: '10.0.2.19:53',
    anomalyScore: 0.9047,
    severity: 'critical',
    status: 'anomalous',
  },
  {
    id: 'evt-006',
    timestamp: '2026-10-20T09:30:02Z',
    requestId: 'req-3906b1',
    flowId: 'flow-011279',
    source: '10.0.17.4',
    destination: '10.0.6.90:80',
    anomalyScore: 0.2145,
    severity: 'info',
    status: 'benign',
  },
  {
    id: 'evt-007',
    timestamp: '2026-10-20T09:28:47Z',
    requestId: 'req-2e5ad83',
    flowId: 'flow-011278',
    source: '198.51.100.8',
    destination: '10.0.11.5:3389',
    anomalyScore: 0.8210,
    severity: 'high',
    status: 'anomalous',
  },
  {
    id: 'evt-008',
    timestamp: '2026-10-20T09:26:33Z',
    requestId: 'req-1d40b7',
    flowId: 'flow-011277',
    source: '10.0.29.88',
    destination: '10.0.3.1:443',
    anomalyScore: 0.2689,
    severity: 'low',
    status: 'benign',
  },
]

// Backend mock configuration displayed in the old "System Information" card.
// Real values are fetched from GET /api/v1/health when the backend is up.
export const dashboardSystemInfo: {
  modelVersion: string
  experimentId: string
  features: number
  threshold: number
  dataset: string
} = {
  modelVersion: 'isolation_forest_v1',
  experimentId: 'with_port',
  features: 60,
  threshold: 0.521919,
  dataset: 'CICIDS2017',
}

// Simple ordered lookup for severity colour classes used across mock pages.
export const severityStyles: Record<string, string> = {
  critical: 'text-red-700 bg-red-50 border-red-200',
  high: 'text-orange-700 bg-orange-50 border-orange-200',
  medium: 'text-yellow-700 bg-yellow-50 border-yellow-200',
  low: 'text-green-700 bg-green-50 border-green-200',
  info: 'text-blue-700 bg-blue-50 border-blue-200',
}