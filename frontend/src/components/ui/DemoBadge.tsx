import { Badge } from '@/components/ui/Badge'
import { FlaskConical } from 'lucide-react'
import { cn } from '@/utils/cn'

interface DemoBadgeProps {
  label?: string
  className?: string
}

// Small pill used to clearly label anything rendered from MOCK / DEMO data.
const DemoBadge = ({ label = 'Demo Data', className }: DemoBadgeProps) => {
  return (
    <Badge variant="info" size="sm" className={cn('gap-1 font-medium', className)}>
      <FlaskConical className="h-3 w-3" />
      {label}
    </Badge>
  )
}

export default DemoBadge