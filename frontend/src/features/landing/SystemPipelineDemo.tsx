import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Database, 
  Cpu, 
  BarChart3, 
  AlertTriangle, 
  Search, 
  FileText,
  ChevronRight
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/Card'
import { sampleFlows } from '@/data/sampleFlows'
import { cn } from '@/utils/cn'

const pipelineStages = [
  {
    id: 'raw-flow',
    title: 'Raw Network Flow',
    description: 'Network traffic data with 60 CICIDS2017 features',
    icon: <Database className="h-6 w-6" />,
    color: 'bg-blue-100 text-blue-600',
  },
  {
    id: 'processing',
    title: 'Preprocessing',
    description: 'Zero-duration handling, log transformations, feature ordering',
    icon: <Cpu className="h-6 w-6" />,
    color: 'bg-purple-100 text-purple-600',
  },
  {
    id: 'detection',
    title: 'Anomaly Detection',
    description: 'E2 Isolation Forest model scoring',
    icon: <BarChart3 className="h-6 w-6" />,
    color: 'bg-green-100 text-green-600',
  },
  {
    id: 'score',
    title: 'Anomaly Score',
    description: 'Numeric anomaly score with threshold comparison',
    icon: <AlertTriangle className="h-6 w-6" />,
    color: 'bg-yellow-100 text-yellow-600',
  },
  {
    id: 'severity',
    title: 'Severity Classification',
    description: 'Risk-based severity level (Info → Critical)',
    icon: <AlertTriangle className="h-6 w-6" />,
    color: 'bg-orange-100 text-orange-600',
  },
  {
    id: 'context',
    title: 'Attack Context',
    description: 'MITRE ATT&CK mapping and knowledge retrieval',
    icon: <Search className="h-6 w-6" />,
    color: 'bg-red-100 text-red-600',
  },
  {
    id: 'report',
    title: 'Intelligence Report',
    description: 'LLM-generated explanation and recommendations',
    icon: <FileText className="h-6 w-6" />,
    color: 'bg-indigo-100 text-indigo-600',
  },
]

const SystemPipelineDemo = () => {
  const [activeStage, setActiveStage] = useState(0)
  const [selectedFlow, setSelectedFlow] = useState(sampleFlows[0])
  const [isPlaying, setIsPlaying] = useState(true)

  // Auto-advance through stages
  useEffect(() => {
    if (!isPlaying) return

    const interval = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % pipelineStages.length)
    }, 2000)

    return () => clearInterval(interval)
  }, [isPlaying])

  const handleStageClick = (index: number) => {
    setActiveStage(index)
    setIsPlaying(false)
  }

  const handleFlowSelect = (flowId: string) => {
    const flow = sampleFlows.find(f => f.id === flowId)
    if (flow) {
      setSelectedFlow(flow)
      setIsPlaying(true)
      setActiveStage(0)
    }
  }

  const getStageContent = (stageId: string) => {
    switch (stageId) {
      case 'raw-flow':
        return (
          <div className="space-y-4">
            <h4 className="font-medium">Sample Flow Data</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500">Destination Port:</span>
                <span className="font-mono ml-2">{selectedFlow.data['Destination Port']}</span>
              </div>
              <div>
                <span className="text-gray-500">Flow Duration:</span>
                <span className="font-mono ml-2">{selectedFlow.data['Flow Duration']} μs</span>
              </div>
              <div>
                <span className="text-gray-500">Total Fwd Packets:</span>
                <span className="font-mono ml-2">{selectedFlow.data['Total Fwd Packets']}</span>
              </div>
              <div>
                <span className="text-gray-500">Total Bwd Packets:</span>
                <span className="font-mono ml-2">{selectedFlow.data['Total Backward Packets']}</span>
              </div>
            </div>
          </div>
        )
      
      case 'processing':
        return (
          <div className="space-y-4">
            <h4 className="font-medium">Preprocessing Steps</h4>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                Zero-duration handling
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                Log1p transformations
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                Feature ordering (60 features)
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                Rate recomputation
              </li>
            </ul>
          </div>
        )
      
      case 'detection':
        return (
          <div className="space-y-4">
            <h4 className="font-medium">Detection Model</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Model:</span>
                <span className="font-medium">Isolation Forest v1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Experiment:</span>
                <span className="font-medium">E2 (with port)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Features:</span>
                <span className="font-medium">60</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Training Data:</span>
                <span className="font-medium">CICIDS2017 Monday</span>
              </div>
            </div>
          </div>
        )
      
      case 'score':
        return (
          <div className="space-y-4">
            <h4 className="font-medium">Score Analysis</h4>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-500">Anomaly Score:</span>
                  <span className="font-mono font-medium">
                    {selectedFlow.expectedScore?.toFixed(4)}
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <motion.div
                    className={cn(
                      'h-full rounded-full',
                      selectedFlow.expectedIsAnomaly 
                        ? 'bg-red-500' 
                        : 'bg-green-500'
                    )}
                    initial={{ width: 0 }}
                    animate={{ 
                      width: `${Math.min((selectedFlow.expectedScore || 0) * 150, 100)}%` 
                    }}
                    transition={{ duration: 1 }}
                  />
                </div>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Threshold (OP-A):</span>
                <span className="font-mono">0.5219</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Status:</span>
                <span className={cn(
                  'font-medium',
                  selectedFlow.expectedIsAnomaly ? 'text-red-600' : 'text-green-600'
                )}>
                  {selectedFlow.expectedIsAnomaly ? 'ANOMALOUS' : 'NORMAL'}
                </span>
              </div>
            </div>
          </div>
        )
      
      case 'severity': {
        const severityLevel = selectedFlow.expectedScore! >= 0.65 ? 'high' : 
                            selectedFlow.expectedScore! >= 0.5219 ? 'medium' : 
                            selectedFlow.expectedScore! >= (0.5219 * 0.9) ? 'low' : 'info'
        
        return (
          <div className="space-y-4">
            <h4 className="font-medium">Severity Classification</h4>
            <div className="space-y-3">
              <div className={cn(
                'px-3 py-2 rounded-lg text-center font-medium',
                severityLevel === 'high' && 'bg-red-100 text-red-700',
                severityLevel === 'medium' && 'bg-yellow-100 text-yellow-700',
                severityLevel === 'low' && 'bg-green-100 text-green-700',
                severityLevel === 'info' && 'bg-blue-100 text-blue-700',
              )}>
                {severityLevel.toUpperCase()}
              </div>
              <div className="text-sm space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Risk Score:</span>
                    <span className="font-mono">{selectedFlow.expectedScore?.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Calibration:</span>
                    <span className="text-gray-600">Initial Placeholder</span>
                  </div>
                </div>
              </div>
            </div>
        )
      }

      case 'context':
        return (
          <div className="space-y-4">
            <h4 className="font-medium">Attack Context</h4>
            <div className="space-y-3">
              <div className="text-sm text-gray-600">
                Future MITRE ATT&CK mapping and RAG knowledge retrieval will be integrated here.
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300" />
                  <span className="text-gray-500">MITRE Techniques:</span>
                  <span className="text-gray-600">Coming Soon</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300" />
                  <span className="text-gray-500">Knowledge Retrieval:</span>
                  <span className="text-gray-600">Coming Soon</span>
                </div>
              </div>
            </div>
          </div>
        )
      
      case 'report':
        return (
          <div className="space-y-4">
            <h4 className="font-medium">Intelligence Report</h4>
            <div className="space-y-3">
              <div className="text-sm text-gray-600">
                Future LLM-generated explanations and actionable recommendations will be provided here.
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300" />
                  <span className="text-gray-500">AI Explanation:</span>
                  <span className="text-gray-600">Coming Soon</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300" />
                  <span className="text-gray-500">Recommendations:</span>
                  <span className="text-gray-600">Coming Soon</span>
                </div>
              </div>
            </div>
          </div>
        )
      
      default:
        return null
    }
  }

  return (
    <div className="space-y-8">
      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
        <div>
          <h3 className="text-lg font-semibold mb-2">Select Sample Flow</h3>
          <div className="flex flex-wrap gap-2">
            {sampleFlows.map((flow) => (
              <button
                key={flow.id}
                onClick={() => handleFlowSelect(flow.id)}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-lg border transition-colors',
                  selectedFlow.id === flow.id
                    ? 'bg-primary-100 border-primary-300 text-primary-700'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                )}
              >
                {flow.name}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 bg-white hover:bg-gray-50"
          >
            {isPlaying ? 'Pause Demo' : 'Play Demo'}
          </button>
        </div>
      </div>

      {/* Pipeline Visualization */}
      <div className="relative">
        {/* Connecting lines */}
        <div className="absolute top-12 left-0 right-0 h-0.5 bg-gray-200 hidden md:block" />
        
        <div className="grid grid-cols-2 md:grid-cols-7 gap-4 md:gap-2">
          {pipelineStages.map((stage, index) => (
            <div key={stage.id} className="relative">
              {/* Stage indicator */}
              <button
                onClick={() => handleStageClick(index)}
                className={cn(
                  'w-full flex flex-col items-center p-4 rounded-xl transition-all duration-300',
                  'border-2 hover:shadow-md',
                  activeStage === index
                    ? 'border-primary-300 bg-primary-50 shadow-sm'
                    : 'border-gray-200 bg-white'
                )}
              >
                <div className={cn(
                  'w-12 h-12 rounded-full flex items-center justify-center mb-3',
                  'transition-transform duration-300',
                  stage.color,
                  activeStage === index && 'scale-110'
                )}>
                  {stage.icon}
                </div>
                <h4 className="font-medium text-sm text-center mb-1">
                  {stage.title}
                </h4>
                <p className="text-xs text-gray-500 text-center line-clamp-2">
                  {stage.description}
                </p>
                
                {/* Active indicator */}
                {activeStage === index && (
                  <motion.div
                    className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-primary-500"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                  />
                )}
              </button>

              {/* Arrow connector (desktop only) */}
              {index < pipelineStages.length - 1 && (
                <div className="hidden md:flex items-center justify-center absolute top-12 -right-4 z-10">
                  <ChevronRight className="h-6 w-6 text-gray-300" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stage Content Display */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeStage}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="border-primary-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-4">
                <div className={cn(
                  'w-10 h-10 rounded-lg flex items-center justify-center',
                  pipelineStages[activeStage].color
                )}>
                  {pipelineStages[activeStage].icon}
                </div>
                <div>
                  <h3 className="font-semibold text-lg">
                    {pipelineStages[activeStage].title}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {pipelineStages[activeStage].description}
                  </p>
                </div>
              </div>
              
              <div className="pt-4 border-t">
                {getStageContent(pipelineStages[activeStage].id)}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>

      {/* Progress indicator */}
      <div className="flex justify-center">
        <div className="flex gap-1">
          {pipelineStages.map((_, index) => (
            <button
              key={index}
              onClick={() => handleStageClick(index)}
              className={cn(
                'w-8 h-2 rounded-full transition-all',
                activeStage === index ? 'bg-primary-600' : 'bg-gray-300'
              )}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default SystemPipelineDemo