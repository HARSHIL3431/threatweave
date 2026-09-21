import { motion } from 'framer-motion'
import { cn } from '@/utils/cn'

interface ScoreIndicatorProps {
  score: number
  threshold: number
  maxScore?: number
  showLabels?: boolean
  showThresholdLine?: boolean
  animated?: boolean
  className?: string
}

const ScoreIndicator = ({
  score,
  threshold,
  maxScore = 1.0,
  showLabels = true,
  showThresholdLine = true,
  animated = true,
  className,
}: ScoreIndicatorProps) => {
  const scorePercentage = Math.min((score / maxScore) * 100, 100)
  const thresholdPercentage = Math.min((threshold / maxScore) * 100, 100)
  
  const getScoreColor = () => {
    if (score >= threshold * 1.5) return 'bg-gradient-to-r from-red-500 to-red-600'
    if (score >= threshold) return 'bg-gradient-to-r from-orange-500 to-yellow-500'
    if (score >= threshold * 0.8) return 'bg-gradient-to-r from-yellow-400 to-green-400'
    return 'bg-gradient-to-r from-green-400 to-green-500'
  }
  
  const getScoreStatus = () => {
    if (score >= threshold) return 'Anomalous'
    if (score >= threshold * 0.8) return 'Suspicious'
    return 'Normal'
  }
  
  const getScoreStatusColor = () => {
    if (score >= threshold) return 'text-red-600'
    if (score >= threshold * 0.8) return 'text-yellow-600'
    return 'text-green-600'
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Score bar */}
      <div className="relative h-6 bg-gray-100 rounded-full overflow-hidden shadow-inner">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-r from-green-400/20 via-yellow-400/20 to-red-400/20" />
        
        {/* Score progress */}
        <motion.div
          className={cn('h-full rounded-full shadow-md', getScoreColor())}
          initial={animated ? { width: 0 } : undefined}
          animate={animated ? { width: `${scorePercentage}%` } : undefined}
          transition={animated ? { duration: 1, ease: "easeOut" } : undefined}
          style={animated ? undefined : { width: `${scorePercentage}%` }}
        />
        
        {/* Threshold line */}
        {showThresholdLine && (
          <div 
            className="absolute top-0 bottom-0 w-0.5 bg-gray-800"
            style={{ left: `${thresholdPercentage}%` }}
          >
            <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 whitespace-nowrap">
              <div className="text-xs font-semibold text-gray-700 bg-white px-2 py-1 rounded shadow-sm">
                Threshold: {threshold.toFixed(4)}
              </div>
            </div>
          </div>
        )}
        
        {/* Score label */}
        <motion.div
          className="absolute top-1/2 transform -translate-y-1/2 text-white text-xs font-bold px-2 py-1 rounded shadow-lg"
          initial={animated ? { left: 0 } : undefined}
          animate={animated ? { left: `${Math.min(scorePercentage, 95)}%` } : undefined}
          transition={animated ? { duration: 1, ease: "easeOut" } : undefined}
          style={animated ? undefined : { left: `${Math.min(scorePercentage, 95)}%` }}
        >
          {score.toFixed(4)}
        </motion.div>
      </div>
      
      {/* Labels and info */}
      {showLabels && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className={cn('w-3 h-3 rounded-full', getScoreColor().replace('bg-gradient-to-r', 'bg-red-500'))} />
              <span className="text-sm font-medium">Score: {score.toFixed(4)}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full border-2 border-gray-800" />
              <span className="text-sm text-gray-600">Threshold: {threshold.toFixed(4)}</span>
            </div>
          </div>
          
          <div className="text-right">
            <div className={cn('text-lg font-bold', getScoreStatusColor())}>
              {getScoreStatus()}
            </div>
            <div className="text-xs text-gray-500">
              Difference: {(score - threshold).toFixed(4)}
            </div>
          </div>
        </div>
      )}
      
      {/* Scale markers */}
      <div className="flex justify-between text-xs text-gray-500 px-1">
        <span>0.0</span>
        <span>{(maxScore * 0.25).toFixed(1)}</span>
        <span>{(maxScore * 0.5).toFixed(1)}</span>
        <span>{(maxScore * 0.75).toFixed(1)}</span>
        <span>{maxScore.toFixed(1)}</span>
      </div>
    </div>
  )
}

export default ScoreIndicator