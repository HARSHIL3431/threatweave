import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import { useSystemHealth } from '@/hooks/useHealth'

const Layout = () => {
  const { data: health, isLoading } = useSystemHealth()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleNavigate = () => {
    setMobileOpen(false)
  }

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <TopBar
        systemHealth={health}
        isLoading={isLoading}
        onMenuClick={() => setMobileOpen((open) => !open)}
      />
      <div className="flex">
        <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} onNavigate={handleNavigate} />
        <main className="flex-1 p-4 md:p-6 lg:p-8 min-w-0">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout