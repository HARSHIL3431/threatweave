import { motion } from 'framer-motion'
import { Activity, Shield, AlertTriangle, BarChart3, Cpu, Database } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { useSystemHealth } from '@/hooks/useHealth'

const StatsOverview = () => {
  const { data: systemHealth, isLoading } = useSystemHealth()

  const stats = [
    {
      title: 'System Status',
      value: systemHealth?.isHealthy ? 'Operational' : 'Degraded',
      icon: <Activity className="h-5 w-5" />,
      color: systemHealth?.isHealthy ? 'text-green-600 bg-green-100' : 'text-yellow-600 bg-yellow-100',
      description: systemHealth?.message || 'Checking system health...',
    },
    {
      title: 'Model Status',
      value: systemHealth?.isModelReady ? 'Ready' : 'Not Ready',
      icon: <Cpu className="h-5 w-5" />,
      color: systemHealth?.isModelReady ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100',
      description: systemHealth?.details?.model_status || 'Checking model status...',
    },
    {
      title: 'Anomaly Threshold',
      value: '0.5219',
      icon: <AlertTriangle className="h-5 w-5" />,
      color: 'text-blue-600 bg-blue-100',
      description: 'OP-A frozen threshold',
    },
    {
      title: 'Features',
      value: '60',
      icon: <Database className="h-5 w-5" />,
      color: 'text-purple-600 bg-purple-100',
      description: 'E2 experiment features',
    },
    {
      title: 'Model Version',
      value: 'v1',
      icon: <Shield className="h-5 w-5" />,
      color: 'text-indigo-600 bg-indigo-100',
      description: 'isolation_forest',
    },
    {
      title: 'Dataset',
      value: 'CICIDS2017',
      icon: <BarChart3 className="h-5 w-5" />,
      color: 'text-orange-600 bg-orange-100',
      description: 'Source dataset',
    },
  ]

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      {stats.map((stat, index) => (
        <motion.div key={index} variants={item}>
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-gray-600">
                  {stat.title}
                </CardTitle>
                <div className={`p-2 rounded-lg ${stat.color}`}>
                  {stat.icon}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <>
                  <Skeleton className="h-7 w-20 mb-2" />
                  <Skeleton className="h-4 w-32" />
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold mb-1">{stat.value}</div>
                  <p className="text-sm text-gray-500">{stat.description}</p>
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  )
}

export default StatsOverview