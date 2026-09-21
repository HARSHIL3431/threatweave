import { Link } from 'react-router-dom'
import { Shield, Bell, User, Wifi, Menu } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import type { SystemStatus } from '@/api/types/health'

interface TopBarProps {
  systemHealth: SystemStatus | undefined
  isLoading: boolean
  onMenuClick?: () => void
}

const TopBar = ({ systemHealth, isLoading, onMenuClick }: TopBarProps) => {
  const getStatusColor = () => {
    if (isLoading) return 'bg-gray-400'
    if (!systemHealth?.isHealthy) return 'bg-red-500'
    if (!systemHealth?.isModelReady) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getStatusText = () => {
    if (isLoading) return 'Checking...'
    if (!systemHealth?.isHealthy) return 'Service Unavailable'
    if (!systemHealth?.isModelReady) return 'Model Not Ready'
    return 'All Systems Operational'
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white">
      <div className="flex h-16 items-center px-4 md:px-6">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-primary-100 text-primary-600">
            <Shield className="h-6 w-6" />
          </div>
          <div className="hidden md:block">
            <h1 className="font-bold text-lg">Anomaly Detection</h1>
            <p className="text-xs text-gray-500">AI-Powered Cybersecurity</p>
          </div>
        </Link>

        {/* Menu (mobile) */}
        <Button variant="ghost" size="icon" className="md:hidden ml-1" onClick={onMenuClick} aria-label="Toggle navigation">
          <Menu className="h-5 w-5" />
        </Button>

        {/* Status Indicator */}
        <div className="ml-2 md:ml-8 flex items-center gap-2 md:gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
            <span className="hidden md:inline text-sm font-medium max-w-[16rem] truncate">
              {getStatusText()}
            </span>
          </div>
          {systemHealth?.isHealthy && systemHealth?.isModelReady && (
            <Badge variant="success" size="sm">
              <Wifi className="h-3 w-3 mr-1" />
              <span className="hidden sm:inline">Connected</span>
              <span className="sm:hidden">OK</span>
            </Badge>
          )}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon">
            <Bell className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon">
            <User className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  )
}

export default TopBar