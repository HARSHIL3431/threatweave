import { forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils/cn'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary-100 text-primary-800 hover:bg-primary-200',
        secondary: 'border-transparent bg-secondary-100 text-secondary-800 hover:bg-secondary-200',
        destructive: 'border-transparent bg-red-100 text-red-800 hover:bg-red-200',
        outline: 'text-foreground border',
        success: 'border-transparent bg-green-100 text-green-800 hover:bg-green-200',
        warning: 'border-transparent bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
        error: 'border-transparent bg-red-100 text-red-800 hover:bg-red-200',
        info: 'border-transparent bg-blue-100 text-blue-800 hover:bg-blue-200',
      },
      size: {
        default: 'px-2.5 py-0.5',
        sm: 'px-2 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(badgeVariants({ variant, size, className }))}
        {...props}
      />
    )
  }
)
Badge.displayName = 'Badge'

export { Badge, badgeVariants }