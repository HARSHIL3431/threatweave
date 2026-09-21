import { NavLink } from 'react-router-dom'
import { Home, BarChart3, Upload, Settings, HelpCircle, FileText, X } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useSystemHealth } from '@/hooks/useHealth'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Detection', href: '/detect', icon: Upload },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Documentation', href: '/docs', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
  { name: 'Help', href: '/help', icon: HelpCircle },
]

interface SidebarProps {
  mobileOpen?: boolean
  onClose?: () => void
  onNavigate?: () => void
}

const Sidebar = ({ mobileOpen = false, onClose, onNavigate }: SidebarProps) => {
  const { data: systemHealth, isLoading } = useSystemHealth()

  const connectionText = isLoading
    ? 'Checking backend…'
    : systemHealth?.isHealthy
      ? 'Connected to FastAPI backend'
      : 'Backend not reachable'

  return (
    <>
      {/* Mobile sidebar backdrop */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed md:relative inset-y-0 left-0 z-50 md:z-auto w-64 flex flex-col border-r bg-white',
          'transform transition-transform duration-300 ease-in-out',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          'md:translate-x-0'
        )}
      >
        {/* Mobile close */}
        <div className="flex items-center justify-between p-4 md:hidden border-b">
          <span className="text-sm font-semibold">Navigation</span>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 overflow-y-auto scrollbar-thin">
          <ul className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.name}>
                  <NavLink
                    to={item.href}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200',
                        isActive
                          ? 'bg-primary-50 text-primary-700 font-medium border border-primary-200'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 active:scale-95'
                      )
                    }
                  >
                    <Icon className="h-5 w-5 flex-shrink-0" />
                    <span className="truncate">{item.name}</span>
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t">
          <div className="text-xs text-gray-500">
            <p className="font-medium mb-1 truncate">Anomaly Detection Platform</p>
            <p className="truncate">v0.1.0 • E2 Experiment</p>
            <p className="mt-2 truncate flex items-center gap-1.5">
              <span
                className={cn(
                  'inline-block w-2 h-2 rounded-full',
                  isLoading
                    ? 'bg-gray-400'
                    : systemHealth?.isHealthy
                      ? 'bg-green-500'
                      : 'bg-red-500'
                )}
              />
              {connectionText}
            </p>
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar