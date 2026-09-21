import { cn } from '@/utils/cn'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  description?: string
  disabled?: boolean
}

// Accessible switch used by the Settings page. `disabled` communicates that
// the control cannot be wired to a backend yet.
const Toggle = ({ checked, onChange, label, description, disabled }: ToggleProps) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'flex items-start gap-3 w-full text-left rounded-lg p-3 border transition-colors',
        checked ? 'border-primary-200 bg-primary-50/50' : 'border-gray-200 bg-white',
        disabled ? 'opacity-60 cursor-not-allowed' : 'hover:bg-gray-50'
      )}
    >
      <span
        className={cn(
          'relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors mt-0.5',
          checked ? 'bg-primary-600' : 'bg-gray-300'
        )}
      >
        <span
          className={cn(
            'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-5' : 'translate-x-0.5'
          )}
        />
      </span>
      {(label || description) && (
        <span className="min-w-0">
          {label && <span className="block text-sm font-medium">{label}</span>}
          {description && <span className="block text-xs text-gray-500 mt-0.5">{description}</span>}
        </span>
      )}
    </button>
  )
}

export default Toggle