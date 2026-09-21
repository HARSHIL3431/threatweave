import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/layout/Layout'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'
import DetectionPage from './pages/DetectionPage'
import AnalyticsPage from './pages/AnalyticsPage'
import DocumentationPage from './pages/DocumentationPage'
import SettingsPage from './pages/SettingsPage'
import HelpPage from './pages/HelpPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<LandingPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="detect" element={<DetectionPage />} />
          <Route path="detection" element={<Navigate to="/detect" replace />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="docs" element={<DocumentationPage />} />
          <Route path="documentation" element={<Navigate to="/docs" replace />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="404" element={<NotFoundPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'var(--background)',
            color: 'var(--foreground)',
            border: '1px solid var(--border)',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: 'white',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: 'white',
            },
          },
        }}
      />
    </>
  )
}

export default App