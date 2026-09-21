import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Upload, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'
import { sampleFlows, getFlowById } from '@/data/sampleFlows'
import { useDetection } from '@/hooks/useDetection'
import { validateFlow } from '@/api/detection'
import type { NetworkFlowRequest, DetectionResponse } from '@/api/types/detection'

interface FlowInputProps {
  onDetectionComplete: (result: DetectionResponse, flow: NetworkFlowRequest) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

// Simplified schema for demonstration
const flowSchema = z.object({
  destinationPort: z.number().min(0).max(65535),
  flowDuration: z.number().min(0),
  totalFwdPackets: z.number().min(0),
  totalBackwardPackets: z.number().min(0),
  totalLengthFwd: z.number().min(0),
  totalLengthBwd: z.number().min(0),
  flowBytesPerS: z.number().min(0),
  flowPacketsPerS: z.number().min(0),
})

type FlowFormData = z.infer<typeof flowSchema>

const FlowInput = ({ onDetectionComplete, isLoading, setIsLoading }: FlowInputProps) => {
  const [selectedSample, setSelectedSample] = useState<string>('benign-flow')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const detectionMutation = useDetection()
  
  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm<FlowFormData>({
    resolver: zodResolver(flowSchema),
    defaultValues: {
      destinationPort: 49188,
      flowDuration: 4,
      totalFwdPackets: 2,
      totalBackwardPackets: 0,
      totalLengthFwd: 12,
      totalLengthBwd: 0,
      flowBytesPerS: 3000000,
      flowPacketsPerS: 500000,
    },
  })

  const handleSampleSelect = (flowId: string) => {
    setSelectedSample(flowId)
    const flow = getFlowById(flowId)
    if (flow) {
      setValue('destinationPort', flow.data['Destination Port'])
      setValue('flowDuration', flow.data['Flow Duration'])
      setValue('totalFwdPackets', flow.data['Total Fwd Packets'])
      setValue('totalBackwardPackets', flow.data['Total Backward Packets'])
      setValue('totalLengthFwd', flow.data['Total Length of Fwd Packets'])
      setValue('totalLengthBwd', flow.data['Total Length of Bwd Packets'])
      setValue('flowBytesPerS', flow.data['Flow Bytes/s'])
      setValue('flowPacketsPerS', flow.data['Flow Packets/s'])
      setError(null)
    }
  }

  const onSubmit = async (data: FlowFormData) => {
    setError(null)
    setIsLoading(true)

    try {
      // Convert form data to full network flow request
      const flow: NetworkFlowRequest = {
        'Destination Port': data.destinationPort,
        'Flow Duration': data.flowDuration,
        'Total Fwd Packets': data.totalFwdPackets,
        'Total Backward Packets': data.totalBackwardPackets,
        'Total Length of Fwd Packets': data.totalLengthFwd,
        'Total Length of Bwd Packets': data.totalLengthBwd,
        'Flow Bytes/s': data.flowBytesPerS,
        'Flow Packets/s': data.flowPacketsPerS,
        // Add remaining fields with default values for demonstration
        'Fwd Packet Length Max': 6.0,
        'Fwd Packet Length Min': 6.0,
        'Fwd Packet Length Mean': 6.0,
        'Fwd Packet Length Std': 0.0,
        'Bwd Packet Length Max': 0.0,
        'Bwd Packet Length Min': 0.0,
        'Bwd Packet Length Mean': 0.0,
        'Bwd Packet Length Std': 0.0,
        'Flow IAT Mean': 4.0,
        'Flow IAT Std': 0.0,
        'Flow IAT Max': 4.0,
        'Flow IAT Min': 4.0,
        'Fwd IAT Total': 4.0,
        'Fwd IAT Mean': 4.0,
        'Fwd IAT Std': 0.0,
        'Fwd IAT Max': 4.0,
        'Fwd IAT Min': 4.0,
        'Bwd IAT Total': 0.0,
        'Bwd IAT Mean': 0.0,
        'Bwd IAT Std': 0.0,
        'Bwd IAT Max': 0.0,
        'Bwd IAT Min': 0.0,
        'Fwd PSH Flags': 0.0,
        'Fwd URG Flags': 0.0,
        'Fwd Header Length': 40.0,
        'Fwd Packets/s': 500000.0,
        'Bwd Packets/s': 0.0,
        'Min Packet Length': 6.0,
        'Max Packet Length': 6.0,
        'Packet Length Mean': 6.0,
        'Packet Length Std': 0.0,
        'Packet Length Variance': 0.0,
        'FIN Flag Count': 0.0,
        'RST Flag Count': 0.0,
        'PSH Flag Count': 0.0,
        'ACK Flag Count': 1.0,
        'URG Flag Count': 1.0,
        'Down/Up Ratio': 0.0,
        'Average Packet Size': 9.0,
        'Init_Win_bytes_forward': 329.0,
        'Init_Win_bytes_backward': -1.0,
        'act_data_pkt_fwd': 1.0,
        'min_seg_size_forward': 20.0,
        'Active Mean': 0.0,
        'Active Std': 0.0,
        'Active Max': 0.0,
        'Active Min': 0.0,
        'Idle Mean': 0.0,
        'Idle Std': 0.0,
        'Idle Max': 0.0,
        'Idle Min': 0.0,
      }

      // Validate the flow
      const validationErrors = validateFlow(flow)
      if (validationErrors.length > 0) {
        setError(`Validation failed: ${validationErrors.join(', ')}`)
        return
      }

      // Submit for detection
      const result = await detectionMutation.mutateAsync(flow)
      onDetectionComplete(result, flow)
      
    } catch (err: any) {
      setError(err.message || 'An error occurred during detection')
      console.error('Detection error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    reset()
    setSelectedSample('benign-flow')
    setError(null)
  }

  return (
    <div className="space-y-6">
      {/* Sample Flow Selection */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Sample Flows</h3>
          <span className="text-sm text-gray-500">Quick test with pre-configured flows</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {sampleFlows.map((flow) => (
            <button
              key={flow.id}
              onClick={() => handleSampleSelect(flow.id)}
              className={`p-4 rounded-lg border text-left transition-all ${
                selectedSample === flow.id
                  ? 'border-primary-300 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  flow.expectedIsAnomaly 
                    ? 'bg-red-100 text-red-600' 
                    : 'bg-green-100 text-green-600'
                }`}>
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="font-medium text-sm">{flow.name}</h4>
                  <p className="text-xs text-gray-500">Expected: {flow.expectedIsAnomaly ? 'Anomalous' : 'Normal'}</p>
                </div>
              </div>
              <p className="text-xs text-gray-600 line-clamp-2">{flow.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="w-full flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:bg-gray-50"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium">Advanced Configuration</span>
          <span className="text-xs text-gray-500">Edit flow parameters manually</span>
        </div>
        {showAdvanced ? (
          <ChevronUp className="h-5 w-5 text-gray-500" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-500" />
        )}
      </button>

      {/* Advanced Form */}
      {showAdvanced && (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Destination Port</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('destinationPort', { valueAsNumber: true })}
              />
              {errors.destinationPort && (
                <p className="text-sm text-red-600">{errors.destinationPort.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Flow Duration (μs)</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('flowDuration', { valueAsNumber: true })}
              />
              {errors.flowDuration && (
                <p className="text-sm text-red-600">{errors.flowDuration.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Total Fwd Packets</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('totalFwdPackets', { valueAsNumber: true })}
              />
              {errors.totalFwdPackets && (
                <p className="text-sm text-red-600">{errors.totalFwdPackets.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Total Bwd Packets</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('totalBackwardPackets', { valueAsNumber: true })}
              />
              {errors.totalBackwardPackets && (
                <p className="text-sm text-red-600">{errors.totalBackwardPackets.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Total Length Fwd (bytes)</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('totalLengthFwd', { valueAsNumber: true })}
              />
              {errors.totalLengthFwd && (
                <p className="text-sm text-red-600">{errors.totalLengthFwd.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Total Length Bwd (bytes)</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('totalLengthBwd', { valueAsNumber: true })}
              />
              {errors.totalLengthBwd && (
                <p className="text-sm text-red-600">{errors.totalLengthBwd.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Flow Bytes/s</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('flowBytesPerS', { valueAsNumber: true })}
              />
              {errors.flowBytesPerS && (
                <p className="text-sm text-red-600">{errors.flowBytesPerS.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Flow Packets/s</label>
              <input
                type="number"
                step="any"
                className="w-full px-3 py-2 border rounded-lg"
                {...register('flowPacketsPerS', { valueAsNumber: true })}
              />
              {errors.flowPacketsPerS && (
                <p className="text-sm text-red-600">{errors.flowPacketsPerS.message}</p>
              )}
            </div>
          </div>
        </form>
      )}

      {/* Error Display */}
      {error && (
        <Alert variant="destructive" title="Detection Error">
          {error}
        </Alert>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 pt-4">
        <Button
          onClick={handleSubmit(onSubmit)}
          loading={isLoading}
          className="gap-2 flex-1"
        >
          <Upload className="h-4 w-4" />
          {isLoading ? 'Analyzing...' : 'Analyze Network Flow'}
        </Button>
        
        <Button
          type="button"
          variant="outline"
          onClick={handleReset}
          disabled={isLoading}
        >
          Reset
        </Button>
      </div>

      {/* Information */}
      <div className="pt-4 border-t text-sm text-gray-600">
        <p className="mb-2">
          <strong>Note:</strong> This demonstration uses simplified flow data. The actual 
          backend requires all 60 features from the E2 experiment schema.
        </p>
        <p>
          Sample flows are from the CICIDS2017 dataset and use the frozen E2 Isolation Forest model.
        </p>
      </div>
    </div>
  )
}

export default FlowInput