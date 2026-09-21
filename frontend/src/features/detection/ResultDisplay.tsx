import { motion } from 'framer-motion'
import { CheckCircle, XCircle, AlertTriangle, Info, Shield } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Alert } from '@/components/ui/Alert'
import ScoreIndicator from '@/components/visualization/ScoreIndicator'
import { formatDetectionResult, getSeverityColor } from '@/api/detection'
import type { DetectionResponse } from '@/api/types/detection'

interface ResultDisplayProps {
  result: DetectionResponse
}

const ResultDisplay = ({ result }: ResultDisplayProps) => {
  const formattedResult = formatDetectionResult(result)
  const severityColor = getSeverityColor(formattedResult.severity)
  
  const getStatusIcon = () => {
    if (formattedResult.isAnomalous) {
      return <XCircle className="h-6 w-6 text-red-600" />
    }
    return <CheckCircle className="h-6 w-6 text-green-600" />
  }

  const getStatusText = () => {
    if (formattedResult.isAnomalous) {
      return 'ANOMALOUS NETWORK FLOW DETECTED'
    }
    return 'NORMAL NETWORK FLOW'
  }

  const getStatusColor = () => {
    if (formattedResult.isAnomalous) {
      return 'text-red-700 bg-red-50 border-red-200'
    }
    return 'text-green-700 bg-green-50 border-green-200'
  }

  return (
    <div className="space-y-6">
      {/* Detection Status */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className={`border rounded-xl p-6 ${getStatusColor()}`}
      >
        <div className="flex items-center gap-4 mb-4">
          {getStatusIcon()}
          <div>
            <h3 className="font-bold text-lg">{getStatusText()}</h3>
            <p className="text-sm opacity-80">
              Anomaly detection completed at {new Date(formattedResult.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm opacity-80">Request ID</p>
            <p className="font-mono text-sm">{result.request_id}</p>
          </div>
          <div>
            <p className="text-sm opacity-80">Experiment</p>
            <p className="font-medium">{formattedResult.experimentId}</p>
          </div>
        </div>
      </motion.div>

      {/* Anomaly Score Visualization */}
      <div className="space-y-4">
        <h4 className="font-medium text-lg">Anomaly Score Analysis</h4>
        
        <ScoreIndicator 
          score={formattedResult.score}
          threshold={formattedResult.threshold}
          showLabels={true}
          showThresholdLine={true}
          animated={true}
          className="p-4 bg-white rounded-xl border shadow-sm"
        />
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-gray-600">Threshold (OP-{formattedResult.operatingPoint})</p>
            <p className="font-mono font-bold">{formattedResult.threshold.toFixed(4)}</p>
          </div>
          <div className={`p-3 rounded-lg ${formattedResult.score >= formattedResult.threshold ? 'bg-red-50' : 'bg-green-50'}`}>
            <p className="text-gray-600">Score Difference</p>
            <p className={`font-mono font-bold ${formattedResult.score >= formattedResult.threshold ? 'text-red-600' : 'text-green-600'}`}>
              {(formattedResult.score - formattedResult.threshold).toFixed(4)}
            </p>
          </div>
        </div>
      </div>

      {/* Severity Classification */}
      <div className="space-y-4">
        <h4 className="font-medium text-lg">Severity Classification</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className={`p-6 rounded-xl border-2 ${severityColor} bg-gradient-to-br from-white to-${severityColor.replace('text-', '')}/5`}>
            <div className="flex items-center gap-3 mb-3">
              <AlertTriangle className={`h-6 w-6 ${severityColor}`} />
              <div>
                <p className="text-sm text-gray-600">Severity Level</p>
                <p className={`text-xl font-bold ${severityColor}`}>
                  {formattedResult.severity.toUpperCase()}
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Based on anomaly score and risk calibration
            </p>
          </div>
          
          <div className="p-6 rounded-xl border border-gray-200 bg-white">
            <div className="flex items-center gap-3 mb-3">
              <Shield className="h-6 w-6 text-gray-600" />
              <div>
                <p className="text-sm text-gray-600">Risk Score</p>
                <p className="text-xl font-bold">{formattedResult.riskScore.toFixed(4)}</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Calibration: {result.severity.calibration_note}
            </p>
          </div>
        </div>
      </div>

      {/* Model Information */}
      <div className="space-y-4">
        <h4 className="font-medium text-lg">Model Information</h4>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
            <p className="text-sm text-gray-600">Version</p>
            <p className="font-medium text-lg">{formattedResult.modelVersion}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
            <p className="text-sm text-gray-600">Experiment</p>
            <p className="font-medium text-lg">{formattedResult.experimentId}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
            <p className="text-sm text-gray-600">Operating Point</p>
            <p className="font-medium text-lg">{formattedResult.operatingPoint}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
            <p className="text-sm text-gray-600">Dataset</p>
            <p className="font-medium text-lg">CICIDS2017</p>
          </div>
        </div>
      </div>

      {/* Future Intelligence Sections */}
      <div className="space-y-4">
        <h4 className="font-medium text-lg">Intelligence Layers</h4>
        
        <div className="space-y-3">
          {/* Attack Context */}
          <Alert variant="info" title="Attack Context">
            <div className="space-y-3">
              <p className="text-sm">
                MITRE ATT&CK mapping and RAG knowledge retrieval will be integrated here in future updates.
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="animate-pulse-subtle">Coming Soon</Badge>
                <Badge variant="outline">MITRE ATT&CK</Badge>
                <Badge variant="outline">Knowledge Retrieval</Badge>
              </div>
            </div>
          </Alert>
          
          {/* Explanation */}
          <Alert variant="info" title="AI Explanation">
            <div className="space-y-3">
              <p className="text-sm">
                LLM-generated explanations and actionable recommendations will be provided here in future updates.
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="animate-pulse-subtle">Coming Soon</Badge>
                <Badge variant="outline">LLM Integration</Badge>
                <Badge variant="outline">Actionable Insights</Badge>
              </div>
            </div>
          </Alert>
        </div>
      </div>

      {/* Raw Data Toggle */}
      <details className="border rounded-xl overflow-hidden">
        <summary className="p-4 font-medium cursor-pointer flex items-center justify-between hover:bg-gray-50 transition-colors">
          <span>View Raw Detection Data</span>
          <Info className="h-4 w-4" />
        </summary>
        <div className="p-4 border-t bg-gray-50">
          <pre className="text-xs bg-white p-4 rounded-lg overflow-auto max-h-60 font-mono">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      </details>
    </div>
  )
}

export default ResultDisplay