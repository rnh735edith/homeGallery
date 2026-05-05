export default function StepSummary({ config }) {
  return (
    <div className="setup-step">
      <h2>Review Configuration</h2>
      <p>Please review your settings before saving. You can edit config.json later.</p>
      <div className="setup-summary">
        <div className="summary-item">
          <span className="summary-label">Photo Directory</span>
          <span className="summary-value">{config.storage.photo_dir}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Admin Username</span>
          <span className="summary-value">{config.admin.username}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Server</span>
          <span className="summary-value">{config.server.host}:{config.server.port}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Database</span>
          <span className="summary-value">{config.database.type}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Auto Thumbnails</span>
          <span className="summary-value">{config.processing.auto_thumbnails ? 'Yes' : 'No'}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Face Detection</span>
          <span className="summary-value">{config.processing.face_detection ? 'Enabled' : 'Disabled'}</span>
        </div>
      </div>
    </div>
  )
}
