// Shared styling for the Recharts tooltip so it matches the app's
// white / rounded / subtle-border card language instead of the default.
export const chartTooltipStyle: React.CSSProperties = {
  background: 'hsl(0 0% 100%)',
  border: '1px solid hsl(214.3 31.8% 91.4%)',
  borderRadius: '0.75rem',
  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
  fontSize: '0.75rem',
  padding: '0.5rem 0.75rem',
}

export const axisTickStyle = {
  fontSize: 11,
  fill: 'hsl(215.4 16.3% 46.9%)',
}

export const gridStrokeStyle = 'hsl(210 40% 96.1%)'