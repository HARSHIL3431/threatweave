import { ReactNode } from 'react'
import { cn } from '@/utils/cn'
import DemoBadge from './DemoBadge'

interface PageHeaderProps {
  title: string
  description?: string
  demo?: boolean
  right?: ReactNode
  className?: string
}

// Consistent header used across the app pages. The `demo` flag renders a
// "Demo Data" pill so mock-backed pages are clearly labelled.
const PageHeader = ({ title, description, demo, right, className }: PageHeaderProps) => {
  return (
    <div
      className={cn(
        'flex flex-col md:flex-row md:items-center justify-between gap-4',
        className
      )}
    >
      <div>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight">{title}</h1>
          {demo && <DemoBadge className="hidden sm:inline-flex" />}
        </div>
        {description && <p className="text-gray-600 mt-2">{description}</p>}
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  )
}

export default PageHeader