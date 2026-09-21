import { useQuery } from '@tanstack/react-query'
import { checkHealth, getSystemStatus } from '@/api/health'

const HEALTH_QUERY_KEY = 'health'

export function useHealth() {
  return useQuery({
    queryKey: [HEALTH_QUERY_KEY],
    queryFn: checkHealth,
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  })
}

export function useSystemHealth() {
  return useQuery({
    queryKey: [HEALTH_QUERY_KEY, 'system'],
    queryFn: getSystemStatus,
    refetchInterval: 30000,
    staleTime: 10000,
  })
}