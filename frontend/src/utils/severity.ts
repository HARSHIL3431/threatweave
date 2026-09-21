import type { BadgeProps } from '@/components/ui/Badge'

// Severity levels mirror the backend SeverityLevel contract.
export type SeverityLevel = 'info' | 'low' | 'medium' | 'high' | 'critical'

// Map a severity level to a <Badge> variant for consistent colouring.
export const severityBadgeVariant: Record<
  SeverityLevel,
  NonNullable<BadgeProps['variant']>
> = {
  info: 'info',
  low: 'success',
  medium: 'warning',
  high: 'error',
  critical: 'destructive',
}

// Hex colours used by Recharts visualisations.
export const severityHexColor: Record<SeverityLevel, string> = {
  info: '#3b82f6',
  low: '#10b981',
  medium: '#f59e0b',
  high: '#ef4444',
  critical: '#dc2626',
}

// Tailwind text classes for inline severity labels.
export const severityTextClass: Record<SeverityLevel, string> = {
  info: 'text-blue-600',
  low: 'text-green-600',
  medium: 'text-yellow-600',
  high: 'text-red-600',
  critical: 'text-red-700',
}