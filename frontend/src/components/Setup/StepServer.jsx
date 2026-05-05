export default function StepServer({ config, updateConfig }) {
  return (
    <div className="setup-step">
      <h2>Server Configuration</h2>
      <p>Configure the server host and port.</p>
      <div className="form-group">
        <label htmlFor="server-host">Host</label>
        <input
          id="server-host"
          type="text"
          value={config.server.host}
          onChange={(e) => updateConfig('server', { host: e.target.value })}
          placeholder="0.0.0.0"
        />
        <small className="form-hint">Use 0.0.0.0 to allow access from other devices on your network</small>
      </div>
      <div className="form-group">
        <label htmlFor="server-port">Port</label>
        <input
          id="server-port"
          type="number"
          value={config.server.port}
          onChange={(e) => updateConfig('server', { port: parseInt(e.target.value) || 8080 })}
          min="1"
          max="65535"
        />
      </div>
    </div>
  )
}
