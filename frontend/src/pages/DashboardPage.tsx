import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Database,
  Radar,
  Server,
  Shield,
  TrendingUp,
  XCircle,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import PageHeader from '@/components/ui/PageHeader'
import ScrollReveal from '@/components/animations/ScrollReveal'
import { useSystemHealth } from '@/hooks/useHealth'
import {
  dashboardKpis,
  detectionActivity,
  severityDistribution,
  recentActivity,
  dashboardSystemInfo,
} from '@/data/mock/dashboard'
import type { MockKpiStat } from '@/data/mock/types'
import { severityBadgeVariant, severityHexColor } from '@/utils/severity'
import { axisTickStyle, chartTooltipStyle, gridStrokeStyle } from '@/utils/charts'
import { cn } from '@/utils/cn'

const DashboardPage = () => {
  const { data: systemHealth, isLoading: healthLoading } = useSystemHealth()

  const totalAnomalies = severityDistribution.reduce((sum, d) => sum + d.count, 0)
  const totalFlows = detectionActivity.reduce((sum, d) => sum + d.total, 0)
  const benignFlows = totalFlows - totalAnomalies

  const statusKpi: MockKpiStat = {
    id: 'system-status',
    label: 'System Status',
    value: systemHealth?.isHealthy ? 'Operational' : 'Unavailable',
    description: systemHealth?.isHealthy ? 'Backend reachable' : 'Backend not reachable',
    icon: Server,
    iconClass: systemHealth?.isHealthy
      ? 'bg-green-100 text-green-600'
      : 'bg-red-100 text-red-600',
  }

  const kpis = [...dashboardKpis, statusKpi]

  const anomalyVsBenign = [
    { name: 'Benign', value: benignFlows, color: '#10b981' },
    { name: 'Anomalous', value: totalAnomalies, color: '#ef4444' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <PageHeader
          title="Security Dashboard"
          description="Monitor anomaly detection activity and system performance"
          demo
          right={
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Activity className="h-4 w-4" />
              <span>Demo Environment</span>
            </div>
          }
        />
      </ScrollReveal>

      {/* KPI Cards */}
      <motion.div
        initial="hidden"
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08 } } }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4"
      >
        {kpis.map((kpi) => {
          const Icon = kpi.icon
          const isSystemStatus = kpi.label === 'System Status'
          return (
            <motion.div
              key={kpi.id}
              variants={{
                hidden: { opacity: 0, y: 16 },
                show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
              }}
            >
              <Card className="h-full hover:shadow-lg transition-shadow duration-300">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-gray-600">
                      {kpi.label}
                    </CardTitle>
                    <div className={cn('p-2 rounded-lg', kpi.iconClass)}>
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {isSystemStatus && healthLoading ? (
                    <>
                      <Skeleton className="h-7 w-24 mb-2" />
                      <Skeleton className="h-4 w-28" />
                    </>
                  ) : (
                    <>
                      <div className="flex items-baseline gap-2">
                        <div className="text-2xl font-bold">{kpi.value}</div>
                        {kpi.trend && (
                          <span className={cn('text-xs font-medium', kpi.trendClass)}>
                            {kpi.trend}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{kpi.description}</p>
                    </>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Activity + Severity Distribution */}
      <div className="grid gap-6 lg:grid-cols-3">
        <ScrollReveal direction="up" distance={20} duration={0.6} className="lg:col-span-2">
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Detection Activity
              </CardTitle>
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-sm bg-primary-500 inline-block" /> Total
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-sm bg-red-500 inline-block" /> Anomalous
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={detectionActivity} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="anomalyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ef4444" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={gridStrokeStyle} vertical={false} />
                  <XAxis dataKey="label" tick={axisTickStyle} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={axisTickStyle} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Area
                    type="monotone"
                    dataKey="total"
                    name="Total"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fill="url(#totalGrad)"
                  />
                  <Area
                    type="monotone"
                    dataKey="anomalous"
                    name="Anomalous"
                    stroke="#ef4444"
                    strokeWidth={2}
                    fill="url(#anomalyGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </ScrollReveal>

        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Radar className="h-5 w-5" />
                Severity Distribution
              </CardTitle>
              <Badge variant="outline">{totalAnomalies} flagged</Badge>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center gap-4">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={severityDistribution}
                      dataKey="count"
                      nameKey="label"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={2}
                      strokeWidth={0}
                    >
                      {severityDistribution.map((d) => (
                        <Cell key={d.level} fill={d.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="w-full space-y-2">
                  {severityDistribution.map((d) => (
                    <div key={d.level} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-gray-600">
                        <span className="w-3 h-3 rounded-full" style={{ background: d.color }} />
                        {d.label}
                      </span>
                      <span className="font-medium">{d.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>
      </div>

      {/* Recent Activity Table */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <Card className="hover:shadow-lg transition-shadow duration-300">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Detection Activity
            </CardTitle>
            <Link to="/detect" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
              Go to Detection
            </Link>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-gray-500 border-b">
                    <th className="py-2 pr-4 font-medium">Timestamp</th>
                    <th className="py-2 pr-4 font-medium">Flow / Request</th>
                    <th className="py-2 pr-4 font-medium">Source</th>
                    <th className="py-2 pr-4 font-medium">Destination</th>
                    <th className="py-2 pr-4 font-medium">Score</th>
                    <th className="py-2 pr-4 font-medium">Severity</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.map((event) => (
                    <tr
                      key={event.id}
                      className="border-b last:border-0 hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-3 pr-4 font-mono text-xs text-gray-500">
                        {new Date(event.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 pr-4">
                        <Link
                          to="/detect"
                          className="font-mono text-xs text-primary-600 hover:underline"
                        >
                          {event.flowId}
                        </Link>
                        <span className="text-gray-400"> · {event.requestId}</span>
                      </td>
                      <td className="py-3 pr-4 font-mono text-xs">{event.source}</td>
                      <td className="py-3 pr-4 font-mono text-xs">{event.destination}</td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-16 rounded-full bg-gray-100 overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${Math.min(event.anomalyScore * 100, 100)}%`,
                                background: severityHexColor[event.severity],
                              }}
                            />
                          </div>
                          <span className="font-mono text-xs">{event.anomalyScore.toFixed(4)}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={severityBadgeVariant[event.severity]} size="sm">
                          {event.severity}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-1.5 text-xs font-medium">
                          {event.status === 'anomalous' ? (
                            <>
                              <XCircle className="h-4 w-4 text-red-600" />
                              <span className="text-red-600">Anomalous</span>
                            </>
                          ) : (
                            <>
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                              <span className="text-green-600">Benign</span>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex justify-end">
              <Link to="/detect" className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 font-medium">
                View detection workflow <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </CardContent>
        </Card>
      </ScrollReveal>

      {/* Anomaly vs Benign + System Information */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ScrollReveal direction="up" distance={20} duration={0.6}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Anomaly vs Benign Flows
              </CardTitle>
              <Badge variant="outline">Demo period</Badge>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={anomalyVsBenign}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={3}
                      strokeWidth={0}
                    >
                      <Cell fill="#10b981" />
                      <Cell fill="#ef4444" />
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-3 w-full">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-green-50">
                    <span className="flex items-center gap-2 text-sm text-green-700">
                      <span className="w-3 h-3 rounded-full bg-green-500" /> Benign
                    </span>
                    <span className="font-bold text-green-700">{benignFlows.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-red-50">
                    <span className="flex items-center gap-2 text-sm text-red-700">
                      <span className="w-3 h-3 rounded-full bg-red-500" /> Anomalous
                    </span>
                    <span className="font-bold text-red-700">{totalAnomalies.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                    <span className="flex items-center gap-2 text-sm text-gray-600">
                      <Activity className="h-4 w-4" /> Detection rate
                    </span>
                    <span className="font-bold">{((totalAnomalies / totalFlows) * 100).toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>

        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                System Information
              </CardTitle>
              {systemHealth?.isHealthy ? (
                <Badge variant="success" size="sm">Connected</Badge>
              ) : (
                <Badge variant="outline" size="sm">{healthLoading ? 'Checking…' : 'Offline'}</Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Model</span>
                  <span className="font-medium font-mono text-sm">
                    {systemHealth?.details.model_version || dashboardSystemInfo.modelVersion}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Experiment</span>
                  <span className="font-medium font-mono text-sm">
                    {systemHealth?.details.experiment_id || dashboardSystemInfo.experimentId}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Operating Point</span>
                  <span className="font-medium">
                    {systemHealth?.details.active_operating_point || 'OP-A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Threshold</span>
                  <span className="font-mono">
                    {systemHealth?.details.active_threshold != null
                      ? systemHealth.details.active_threshold.toFixed(6)
                      : dashboardSystemInfo.threshold.toFixed(6)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Features</span>
                  <span className="font-medium">{dashboardSystemInfo.features}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Source Dataset</span>
                  <span className="font-medium">{dashboardSystemInfo.dataset}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500 border-t pt-3">
                <Database className="h-4 w-4" />
                {systemHealth?.isHealthy
                  ? 'Configuration reported by the live health endpoint.'
                  : 'Showing demo defaults — backend not reachable.'}
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>
      </div>

      {/* CTA strip to Detection */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <Card className="bg-gradient-to-r from-primary-50 to-blue-50 border-primary-200 hover:shadow-lg transition-shadow duration-300">
          <CardContent className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-primary-100 text-primary-600">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Need a real detection?</h3>
                <p className="text-sm text-gray-600">
                  Submit a network flow and get a live result from the backend ML pipeline.
                </p>
              </div>
            </div>
            <Link to="/detect" className="inline-flex items-center gap-1 text-primary-700 hover:text-primary-800 font-medium">
              Run analysis <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>
      </ScrollReveal>
    </div>
  )
}

export default DashboardPage