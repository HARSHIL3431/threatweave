import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  BarChart3,
  Gauge,
  Layers,
  ListOrdered,
  PieChart as PieChartIcon,
  Radio,
  ScanSearch,
  TrendingUp,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
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
import PageHeader from '@/components/ui/PageHeader'
import ScrollReveal from '@/components/animations/ScrollReveal'
import {
  analyticsTimeRanges,
  analyticsSeverityDistribution,
  anomalyScoreDistribution,
  detectionTrends,
  protocolDistribution,
  topPatterns,
  trafficStats,
  trafficSummary,
} from '@/data/mock/analytics'
import { severityBadgeVariant, severityHexColor } from '@/utils/severity'
import { axisTickStyle, chartTooltipStyle, gridStrokeStyle } from '@/utils/charts'
import { cn } from '@/utils/cn'

const AnalyticsPage = () => {
  const [selectedRange, setSelectedRange] = useState<string>(analyticsTimeRanges[1])

  return (
    <div className="space-y-8">
      {/* Header */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <PageHeader
          title="Analytics"
          description="Detection trends, distributions and traffic statistics"
          demo
          right={
            <div className="flex flex-wrap items-center gap-1 p-1 rounded-lg border bg-white">
              {analyticsTimeRanges.map((range) => (
                <button
                  key={range}
                  onClick={() => setSelectedRange(range)}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                    selectedRange === range
                      ? 'bg-primary-600 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  )}
                >
                  {range}
                </button>
              ))}
            </div>
          }
        />
      </ScrollReveal>

      {/* Traffic statistics cards */}
      <motion.div
        initial="hidden"
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.06 } } }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4"
      >
        {trafficStats.map((stat) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.id}
              variants={{
                hidden: { opacity: 0, y: 16 },
                show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
              }}
            >
              <Card className="h-full hover:shadow-lg transition-shadow duration-300">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-gray-600">{stat.label}</CardTitle>
                    <div className={cn('p-2 rounded-lg', stat.iconClass)}>
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {stat.value}
                    <span className="text-sm font-medium text-gray-500 ml-1">{stat.unit}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{stat.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Detection Trends + Severity Distribution */}
      <div className="grid gap-6 lg:grid-cols-3">
        <ScrollReveal direction="up" distance={20} duration={0.6} className="lg:col-span-2">
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Detection Trends
              </CardTitle>
              <Badge variant="outline">{selectedRange}</Badge>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={detectionTrends} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={gridStrokeStyle} vertical={false} />
                  <XAxis dataKey="label" tick={axisTickStyle} tickLine={false} axisLine={false} />
                  <YAxis tick={axisTickStyle} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Area
                    type="monotone"
                    dataKey="value"
                    name="Detections"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fill="url(#trendGrad)"
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
                <PieChartIcon className="h-5 w-5" />
                Severity Distribution
              </CardTitle>
              <Badge variant="outline">
                {analyticsSeverityDistribution.reduce((s, d) => s + d.count, 0)} flagged
              </Badge>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={analyticsSeverityDistribution}
                    dataKey="count"
                    nameKey="label"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {analyticsSeverityDistribution.map((d) => (
                      <Cell key={d.level} fill={d.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={chartTooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="w-full space-y-2 mt-2">
                {analyticsSeverityDistribution.map((d) => (
                  <div key={d.level} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-gray-600">
                      <span className="w-3 h-3 rounded-full" style={{ background: d.color }} />
                      {d.label}
                    </span>
                    <span className="font-medium">{d.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>
      </div>

      {/* Score Distribution + Protocol Distribution */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ScrollReveal direction="up" distance={20} duration={0.6}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Anomaly Score Distribution
              </CardTitle>
              <Gauge className="h-5 w-5 text-gray-400" />
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={anomalyScoreDistribution} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke={gridStrokeStyle} vertical={false} />
                  <XAxis dataKey="range" tick={axisTickStyle} tickLine={false} axisLine={false} />
                  <YAxis tick={axisTickStyle} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={chartTooltipStyle} cursor={{ fill: 'rgba(37, 99, 235, 0.06)' }} />
                  <Bar dataKey="count" name="Flows" fill="#2563eb" radius={[4, 4, 0, 0]} maxBarSize={40}>
                    {anomalyScoreDistribution.map((bucket, i) => (
                      <Cell
                        key={bucket.range}
                        fill={i >= 3 ? '#ef4444' : i >= 2 ? '#f59e0b' : '#2563eb'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </ScrollReveal>

        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Radio className="h-5 w-5" />
                Protocol Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <ResponsiveContainer width="100%" height={210}>
                  <PieChart>
                    <Pie
                      data={protocolDistribution}
                      dataKey="percentage"
                      nameKey="protocol"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={2}
                      strokeWidth={0}
                    >
                      {protocolDistribution.map((p) => (
                        <Cell key={p.protocol} fill={p.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle} formatter={(value) => `${value}%`} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="w-full space-y-3">
                  {protocolDistribution.map((p) => (
                    <div key={p.protocol}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="flex items-center gap-2 text-gray-600">
                          <span className="w-3 h-3 rounded-full" style={{ background: p.color }} />
                          {p.protocol}
                        </span>
                        <span className="font-medium">{p.percentage}%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${p.percentage}%`, background: p.color }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>
      </div>

      {/* Top Detected Patterns + Traffic summary */}
      <div className="grid gap-6 lg:grid-cols-3">
        <ScrollReveal direction="up" distance={20} duration={0.6} className="lg:col-span-2">
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <ScanSearch className="h-5 w-5" />
                Top Detected Patterns
              </CardTitle>
              <ListOrdered className="h-5 w-5 text-gray-400" />
            </CardHeader>
            <CardContent className="space-y-2">
              {topPatterns.map((pattern, index) => (
                <div
                  key={pattern.id}
                  className="flex items-center gap-4 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <span className="w-6 h-6 flex items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600 flex-shrink-0">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">{pattern.name}</span>
                      <Badge variant="outline" size="sm">{pattern.category}</Badge>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="h-1.5 flex-1 max-w-[220px] rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min((pattern.count / 120) * 100, 100)}%`,
                            background: severityHexColor[pattern.severity],
                          }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{pattern.count} hits</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge variant={severityBadgeVariant[pattern.severity]} size="sm">
                      {pattern.severity}
                    </Badge>
                    <span className="font-mono text-xs text-gray-500">
                      {pattern.score.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </ScrollReveal>

        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5" />
                Traffic Summary
              </CardTitle>
              <Activity className="h-5 w-5 text-gray-400" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-xl bg-green-50">
                <p className="text-sm text-green-700 font-medium">Benign share</p>
                <p className="text-2xl font-bold text-green-700">
                  {trafficSummary.benignSharePercentage}%
                </p>
              </div>
              <div className="p-4 rounded-xl bg-red-50">
                <p className="text-sm text-red-700 font-medium">Anomalous share</p>
                <p className="text-2xl font-bold text-red-700">
                  {trafficSummary.anomalousSharePercentage}%
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-orange-50">
                  <p className="text-xs text-orange-700 font-medium">High-risk share</p>
                  <p className="text-lg font-bold text-orange-700">
                    {trafficSummary.highRiskSharePercentage}%
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-blue-50">
                  <p className="text-xs text-blue-700 font-medium">Average score</p>
                  <p className="text-lg font-bold text-blue-700">
                    {trafficSummary.avgScore.toFixed(2)}
                  </p>
                </div>
              </div>
              <p className="text-xs text-gray-500">
                Charts use centralized demo data until the analytics API is exposed.
              </p>
            </CardContent>
          </Card>
        </ScrollReveal>
      </div>
    </div>
  )
}

export default AnalyticsPage