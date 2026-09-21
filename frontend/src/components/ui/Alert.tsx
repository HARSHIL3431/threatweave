import { forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils/cn'
import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react'

const alertVariants = cva(
  'relative w-full rounded-lg border p-4',
  {
    variants: {
      variant: {
        default: 'bg-background text-foreground',
        destructive: 'border-red-200 bg-red-50 text-red-800',
        warning: 'border-yellow-200 bg-yellow-50 text-yellow-800',
        success: 'border-green-200 bg-green-50 text-green-800',
        info: 'border-blue-200 bg-blue-50 text-blue-800',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

const iconMap = {
  default: Info,
  destructive: XCircle,
  warning: AlertCircle,
  success: CheckCircle,
  info: Info,
}

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string
}

const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, title, children, ...props }, ref) => {
    const Icon = iconMap[variant || 'default']

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(alertVariants({ variant }), className)}
        {...props}
      >
        <div className="flex items-start gap-3">
          <Icon className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            {title && (
              <h5 className="font-medium mb-1">
                {title}
              </h5>
            )}
            <div className="text-sm">
              {children}
            </div>
          </div>
        </div>
      </div>
    )
  }
)
Alert.displayName = 'Alert'

export { Alert, alertVariants }