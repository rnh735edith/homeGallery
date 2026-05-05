export default function StepProcessing({ config, updateConfig }) {
  return (
    <div className="setup-step">
      <h2>Background Processing</h2>
      <p>Configure automatic processing options. These can be changed later.</p>
      <div className="form-group">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={config.processing.auto_thumbnails}
            onChange={(e) => updateConfig('processing', { auto_thumbnails: e.target.checked })}
          />
          <span>Auto-generate thumbnails on upload</span>
        </label>
      </div>
      <div className="form-group">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={config.processing.face_detection}
            onChange={(e) => updateConfig('processing', { face_detection: e.target.checked })}
          />
          <span>Run face detection in background (requires more memory)</span>
        </label>
      </div>
    </div>
  )
}
