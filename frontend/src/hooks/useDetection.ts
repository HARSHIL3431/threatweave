import { useMutation } from '@tanstack/react-query'
import { detectFlow, detectBatch } from '@/api/detection'

const DETECTION_MUTATION_KEY = 'detection'

export function useDetection() {
  return useMutation({
    mutationKey: [DETECTION_MUTATION_KEY, 'single'],
    mutationFn: detectFlow,
    onError: (error) => {
      console.error('Detection error:', error)
    },
  })
}

export function useBatchDetection() {
  return useMutation({
    mutationKey: [DETECTION_MUTATION_KEY, 'batch'],
    mutationFn: detectBatch,
    onError: (error) => {
      console.error('Batch detection error:', error)
    },
  })
}

// Helper hook for managing detection state
export function useDetectionManager() {
  const detectionMutation = useDetection()
  const batchDetectionMutation = useBatchDetection()

  return {
    detectSingle: detectionMutation.mutateAsync,
    detectBatch: batchDetectionMutation.mutateAsync,
    isDetecting: detectionMutation.isPending || batchDetectionMutation.isPending,
    error: detectionMutation.error || batchDetectionMutation.error,
    reset: () => {
      detectionMutation.reset()
      batchDetectionMutation.reset()
    },
  }
}