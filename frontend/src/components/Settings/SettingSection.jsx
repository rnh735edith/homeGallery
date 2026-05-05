const icons = {
  server: '\u{1F5A5}',
  folder: '\u{1F4C2}',
  gear: '\u2699',
  shield: '\u{1F6E1}',
}

export default function SettingSection({ title, icon, children }) {
  return (
    <div className="setting-section">
      <h3>
        <span className="section-icon">{icons[icon] || '\u{1F4CB}'}</span>
        {title}
      </h3>
      {children}
    </div>
  )
}
