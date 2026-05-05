export default function StepDatabase({ config, updateConfig }) {
  const handleDbTypeChange = (type) => {
    const url = type === 'postgresql'
      ? 'postgresql://user:password@localhost:5432/homegallery'
      : 'sqlite:///./data/gallery.db'
    updateConfig('database', { type, url })
  }

  return (
    <div className="setup-step">
      <h2>Database</h2>
      <p>Choose your database type. SQLite is recommended for single-user setups.</p>
      <div className="form-group">
        <label>Database Type</label>
        <div className="radio-group">
          <label className="radio-label">
            <input
              type="radio"
              name="db-type"
              value="sqlite"
              checked={config.database.type === 'sqlite'}
              onChange={() => handleDbTypeChange('sqlite')}
            />
            <span>SQLite (Local, recommended for single user)</span>
          </label>
          <label className="radio-label">
            <input
              type="radio"
              name="db-type"
              value="postgresql"
              checked={config.database.type === 'postgresql'}
              onChange={() => handleDbTypeChange('postgresql')}
            />
            <span>PostgreSQL (Remote, for scaling)</span>
          </label>
        </div>
      </div>
      {config.database.type === 'postgresql' && (
        <div className="form-group">
          <label htmlFor="db-url">Connection URL</label>
          <input
            id="db-url"
            type="text"
            value={config.database.url}
            onChange={(e) => updateConfig('database', { url: e.target.value })}
            placeholder="postgresql://user:password@localhost:5432/homegallery"
          />
        </div>
      )}
    </div>
  )
}
