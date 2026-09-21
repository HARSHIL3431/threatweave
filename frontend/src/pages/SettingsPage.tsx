import { useState } from 'react'
import {
  Bell,
  CheckCircle2,
  Gauge,
  Globe,
  Info,
  RefreshCcw,
  Save,
  Server,
  SlidersHorizontal,
  Wrench,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'
import Toggle from '@/components/ui/Toggle'
import PageHeader from '@/components/ui/PageHeader'
import ScrollReveal from '@/components/animations/ScrollReveal'
import { useSystemHealth } from '@/hooks/useHealth'
import { usePersistentState } from '@/hooks/usePersistentState'
import {
  localSettingLabel,
  settingsDetectionDefaults,
  settingsDetectionModeOptions,
  settingsEnvironmentOptions,
  settingsGeneralDefaults,
  settingsNotificationDefaults,
  settingsOperatingPointOptions,
  settingsSystemDefaults,
  settingsThemeOptions,
} from '@/data/mock/settings'
import { toast } from 'react-hot-toast'

const SettingsPage = () => {
  const { data: systemHealth, isLoading: healthLoading } = useSystemHealth()

  // General
  const [appName, setAppName] = usePersistentState('settings.appName', settingsGeneralDefaults.appName)
  const [environment, setEnvironment] = usePersistentState('settings.environment', settingsGeneralDefaults.environment)
  const [theme, setTheme] = usePersistentState('settings.theme', settingsGeneralDefaults.themePreference)

  // Detection
  const [operatingPoint, setOperatingPoint] = usePersistentState('settings.op', settingsDetectionDefaults.operatingPoint)
  const [thresholdDisplay, setThresholdDisplay] = usePersistentState('settings.threshold', settingsDetectionDefaults.thresholdDisplay)
  const [detectionMode, setDetectionMode] = usePersistentState('settings.mode', settingsDetectionDefaults.detectionMode)

  // Notifications
  const [notifications, setNotifications] = usePersistentState('settings.notifications', settingsNotificationDefaults)

  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    toast.success('Settings saved locally in this browser')
    setSaved(true)
    window.setTimeout(() => setSaved(false), 3000)
  }

  const handleReset = () => {
    setAppName(settingsGeneralDefaults.appName)
    setEnvironment(settingsGeneralDefaults.environment)
    setTheme(settingsGeneralDefaults.themePreference)
    setOperatingPoint(settingsDetectionDefaults.operatingPoint)
    setThresholdDisplay(settingsDetectionDefaults.thresholdDisplay)
    setDetectionMode(settingsDetectionDefaults.detectionMode)
    setNotifications(settingsNotificationDefaults)
    toast.success('Local settings restored to defaults')
  }

  const connected = systemHealth?.isHealthy === true
  const thresholdValue =
    systemHealth?.details.active_threshold != null
      ? systemHealth.details.active_threshold.toFixed(6)
      : settingsSystemDefaults.threshold.toFixed(6)
  const systemOperatingPoint =
    systemHealth?.details.active_operating_point || settingsSystemDefaults.operatingPoint

  const selectClass =
    'w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-300'

  return (
    <div className="space-y-8">
      {/* Header */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <PageHeader
          title="Settings"
          description="Application and detection configuration"
          demo
          right={
            <>
              <Button variant="outline" className="gap-2" onClick={handleReset}>
                <RefreshCcw className="h-4 w-4" />
                Reset
              </Button>
              <Button className="gap-2" onClick={handleSave}>
                <Save className="h-4 w-4" />
                Save
              </Button>
            </>
          }
        />
      </ScrollReveal>

      <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
        <Alert variant="info" title="Local / Demo settings">
          These controls update local browser state only. They do not modify the backend unless a
          real configuration endpoint is connected. Saved preferences persist across refreshes.
          {saved && (
            <div className="mt-2 flex items-center gap-1.5 text-green-700">
              <CheckCircle2 className="h-4 w-4" /> Saved
            </div>
          )}
        </Alert>
      </ScrollReveal>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* General */}
        <ScrollReveal direction="up" distance={20} duration={0.6}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Wrench className="h-5 w-5" />
                General
              </CardTitle>
              <Badge variant="info" size="sm">{localSettingLabel}</Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Application name</label>
                <input
                  value={appName}
                  onChange={(e) => setAppName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-300"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Environment</label>
                  <select
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                    className={selectClass}
                  >
                    {settingsEnvironmentOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Theme preference</label>
                  <select
                    value={theme}
                    onChange={(e) => setTheme(e.target.value)}
                    className={selectClass}
                  >
                    {settingsThemeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>

        {/* Detection */}
        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Gauge className="h-5 w-5" />
                Detection
              </CardTitle>
              <Badge variant="info" size="sm">{localSettingLabel}</Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Operating point</label>
                <select
                  value={operatingPoint}
                  onChange={(e) => setOperatingPoint(e.target.value)}
                  className={selectClass}
                >
                  {settingsOperatingPointOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500">
                  The backend serves a single frozen operating point (currently {systemOperatingPoint}) — this select is a local preference until a tuning endpoint exists.
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Threshold display</label>
                <input
                  value={thresholdDisplay}
                  onChange={(e) => setThresholdDisplay(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-300"
                />
                <p className="text-xs text-gray-500">
                  Active threshold reported by the backend: <span className="font-mono">{thresholdValue}</span>
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Detection mode</label>
                <select
                  value={detectionMode}
                  onChange={(e) => setDetectionMode(e.target.value)}
                  className={selectClass}
                >
                  {settingsDetectionModeOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>
        </ScrollReveal>

        {/* Notifications */}
        <ScrollReveal direction="up" distance={20} duration={0.6}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Notifications
              </CardTitle>
              <Badge variant="info" size="sm">{localSettingLabel}</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <Toggle
                checked={notifications.detectionAlerts}
                onChange={(v) => setNotifications({ ...notifications, detectionAlerts: v })}
                label="Detection alerts"
                description="Notify when a flow is flagged anomalous"
              />
              <Toggle
                checked={notifications.severityAlerts}
                onChange={(v) => setNotifications({ ...notifications, severityAlerts: v })}
                label="Severity alerts"
                description="Alert on high and critical severity only"
              />
              <Toggle
                checked={notifications.reportNotifications}
                onChange={(v) => setNotifications({ ...notifications, reportNotifications: v })}
                label="Report notifications"
                description="Notify when a report has been generated"
              />
            </CardContent>
          </Card>
        </ScrollReveal>

        {/* System */}
        <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
          <Card className="h-full hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                System
              </CardTitle>
              {healthLoading ? (
                <Badge variant="outline" size="sm">Checking…</Badge>
              ) : connected ? (
                <Badge variant="success" size="sm">
                  <CheckCircle2 className="h-3 w-3 mr-1" /> Connected
                </Badge>
              ) : (
                <Badge variant="destructive" size="sm">Offline</Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between items-center p-3 rounded-lg bg-gray-50">
                <span className="text-sm text-gray-600 flex items-center gap-2">
                  <Globe className="h-4 w-4" /> Backend URL
                </span>
                <span className="font-mono text-sm">{settingsSystemDefaults.backendUrl}</span>
              </div>
              <div className="flex justify-between p-3 rounded-lg bg-gray-50">
                <span className="text-sm text-gray-600">Connection</span>
                <span className="text-sm font-medium">
                  {healthLoading
                    ? 'Checking…'
                    : connected
                      ? 'Backend reachable'
                      : 'Backend unreachable'}
                </span>
              </div>
              <div className="flex justify-between p-3 rounded-lg bg-gray-50">
                <span className="text-sm text-gray-600">Model version</span>
                <span className="text-sm font-medium font-mono">
                  {systemHealth?.details.model_version || settingsSystemDefaults.modelVersion}
                </span>
              </div>
              <div className="flex justify-between p-3 rounded-lg bg-gray-50">
                <span className="text-sm text-gray-600">Experiment ID</span>
                <span className="text-sm font-medium font-mono">
                  {systemHealth?.details.experiment_id || settingsSystemDefaults.experimentId}
                </span>
              </div>
              <div className="flex justify-between p-3 rounded-lg bg-gray-50">
                <span className="text-sm text-gray-600">Operating point</span>
                <span className="text-sm font-medium">{systemOperatingPoint}</span>
              </div>
              <div className="flex justify-between p-3 rounded-lg bg-gray-50">
                <span className="text-sm text-gray-600">Threshold</span>
                <span className="text-sm font-medium font-mono">{thresholdValue}</span>
              </div>
              <div className="flex justify-between p-3 rounded-lg bg-gray-50">
                <span className="text-sm text-gray-600">Features / Dataset</span>
                <span className="text-sm font-medium">
                  {settingsSystemDefaults.features} · {settingsSystemDefaults.dataset}
                </span>
              </div>
              <p className="flex items-start gap-2 text-xs text-gray-500 pt-2">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                {connected
                  ? 'Values above are reported by the live health endpoint.'
                  : 'Backend is not reachable — showing demo defaults.'}
              </p>
            </CardContent>
          </Card>
        </ScrollReveal>
      </div>

      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <Card className="border-dashed">
          <CardContent className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <SlidersHorizontal className="h-4 w-4" />
              Settings are stored locally in your browser and do not affect other users.
            </div>
            <Button variant="outline" className="gap-2" onClick={handleReset}>
              <RefreshCcw className="h-4 w-4" />
              Restore defaults
            </Button>
          </CardContent>
        </Card>
      </ScrollReveal>
    </div>
  )
}

export default SettingsPage