const icons = {
  cpu: '\u{1F4BB}',
  memory: '\u{1F9E0}',
  photo: '\u{1F5BC}',
  grid: '\u26DE',
  disk: '\u{1F4BF}',
  database: '\u{1F5C4}',
}

export default function MetricCard({ title, value, subtitle, icon, color = 'primary' }) {
  return (
    <div className={`metric-card metric-${color}`}>
      <div className="metric-header">
        <span className="metric-icon">{icons[icon] || '\u{1F4CB}'}</span>
        <span className="metric-title">{title}</span>
      </div>
      <div className="metric-value">{value}</div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  )
}
