const levelColors = {
  INFO: 'log-info',
  WARNING: 'log-warn',
  ERROR: 'log-error',
  DEBUG: 'log-debug',
}

export default function LogViewer({ logs }) {
  if (logs.length === 0) {
    return <p className="empty-logs">No logs available</p>
  }

  return (
    <div className="log-viewer">
      {logs.map((log, i) => (
        <div key={i} className={`log-entry ${levelColors[log.level] || 'log-info'}`}>
          <span className="log-time">{log.timestamp?.split(' ')[1] || ''}</span>
          <span className="log-level">{log.level}</span>
          <span className="log-message">{log.message}</span>
        </div>
      ))}
    </div>
  )
}
