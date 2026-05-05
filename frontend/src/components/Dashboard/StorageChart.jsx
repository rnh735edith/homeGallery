export default function StorageChart({ storage }) {
  const diskPct = storage.disk.percent_used
  const photoPct = storage.photos.size_mb > 0 ? (storage.photos.size_mb / (storage.disk.total_gb * 1024) * 100) : 0
  const thumbPct = storage.thumbnails.size_mb > 0 ? (storage.thumbnails.size_mb / (storage.disk.total_gb * 1024) * 100) : 0

  return (
    <div className="storage-chart">
      <div className="chart-bar-container">
        <div className="chart-label">Disk Usage</div>
        <div className="chart-bar">
          <div className="chart-fill" style={{ width: `${diskPct}%` }}>
            <span className="chart-label-inside">{diskPct}%</span>
          </div>
        </div>
      </div>

      <div className="chart-breakdown">
        <div className="breakdown-item">
          <span className="breakdown-dot dot-photos" />
          <span>Photos: {storage.photos.count} ({storage.photos.size_mb} MB)</span>
        </div>
        <div className="breakdown-item">
          <span className="breakdown-dot dot-thumbnails" />
          <span>Thumbnails: {storage.thumbnails.count} ({storage.thumbnails.size_mb} MB)</span>
        </div>
        <div className="breakdown-item">
          <span className="breakdown-dot dot-database" />
          <span>Database: {storage.database.size_mb} MB ({storage.database.type})</span>
        </div>
        <div className="breakdown-item">
          <span className="breakdown-dot dot-free" />
          <span>Free: {storage.disk.free_gb} GB</span>
        </div>
      </div>

      <div className="chart-stats">
        <div className="stat">
          <span>Total</span>
          <strong>{storage.disk.total_gb} GB</strong>
        </div>
        <div className="stat">
          <span>Used</span>
          <strong>{storage.disk.used_gb} GB</strong>
        </div>
        <div className="stat">
          <span>Free</span>
          <strong>{storage.disk.free_gb} GB</strong>
        </div>
      </div>
    </div>
  )
}
