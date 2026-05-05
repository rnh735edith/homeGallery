export default function StepAdmin({ config, updateConfig }) {
  return (
    <div className="setup-step">
      <h2>Admin Account</h2>
      <p>Create the admin account for your HomeGallery server.</p>
      <div className="form-group">
        <label htmlFor="admin-username">Username</label>
        <input
          id="admin-username"
          name="username"
          type="text"
          value={config.admin.username}
          onChange={(e) => updateConfig('admin', { username: e.target.value })}
          placeholder="admin"
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="admin-password">Password</label>
        <input
          id="admin-password"
          name="password"
          type="password"
          value={config.admin.password}
          onChange={(e) => updateConfig('admin', { password: e.target.value })}
          placeholder="Minimum 6 characters"
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="admin-confirm">Confirm Password</label>
        <input
          id="admin-confirm"
          name="confirm_password"
          type="password"
          value={config.admin.confirmPassword}
          onChange={(e) => updateConfig('admin', { confirmPassword: e.target.value })}
          placeholder="Re-enter password"
          required
        />
      </div>
    </div>
  )
}
