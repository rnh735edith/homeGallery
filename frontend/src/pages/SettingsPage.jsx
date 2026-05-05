import { useEffect, useState } from "react";
import api from "../services/api";
import AgentCard from "../components/Settings/AgentCard";
import useAgentStore from "../stores/agentStore";
import SettingSection from "../components/Settings/SettingSection";

const API_PROVIDERS = [
  { value: "openai", label: "OpenAI (ChatGPT)" },
  { value: "gemini", label: "Google Gemini" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "anthropic", label: "Anthropic (Claude)" },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("general");
  const [formData, setFormData] = useState({
    server: { host: "0.0.0.0", port: 8080 },
    storage: { photo_dir: "", thumbnail_dir: "", face_encoding_dir: "" },
    processing: {
      auto_thumbnails: true,
      face_detection: true,
      face_processing_max_memory_mb: 512,
      max_concurrent_tasks: 2,
    },
    security: { jwt_expire_minutes: 1440 },
  });
  const [sysStatus, setSysStatus] = useState(null);
  const [dbStatus, setDbStatus] = useState(null);
  const [folderPath, setFolderPath] = useState("");
  const [folderEntries, setFolderEntries] = useState([]);
  const [browseLoading, setBrowseLoading] = useState(false);
  const [backupLoading, setBackupLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [wipeConfirm, setWipeConfirm] = useState("");
  const [wipeType, setWipeType] = useState("");
  const [apiKeys, setApiKeys] = useState([]);
  const [apiKeysLoading, setApiKeysLoading] = useState(false);
  const [showAddKey, setShowAddKey] = useState(false);
  const [newKey, setNewKey] = useState({
    provider: "openai",
    name: "",
    key: "",
  });
  const [editingKey, setEditingKey] = useState(null);
  const [contactMessages, setContactMessages] = useState([]);
  const [contactLoading, setContactLoading] = useState(false);
  const [networkInfo, setNetworkInfo] = useState(null);
  const [telegramConfig, setTelegramConfig] = useState(null);
  const [telegramTesting, setTelegramTesting] = useState(false);
  const [telegramTestResult, setTelegramTestResult] = useState(null);

  const fetchAgents = useAgentStore((state) => state.fetchAgents);
  const agents = useAgentStore((state) => state.agents);
  const agentsLoading = useAgentStore((state) => state.loading);
  const agentsError = useAgentStore((state) => state.error);

  useEffect(() => {
    loadSettings();
    loadStatus();
    loadNetworkInfo();
  }, []);

  useEffect(() => {
    if (activeTab === "agents") {
      fetchAgents();
    }
    if (activeTab === "api-keys") {
      loadApiKeys();
    }
    if (activeTab === "messages") {
      loadContactMessages();
    }
    if (activeTab === "notifications") {
      loadTelegramConfig();
    }
  }, [activeTab]);

  const loadSettings = async () => {
    try {
      const res = await api.get("/settings/");
      if (res.data.configured) {
        setSettings(res.data);
        setFormData({
          server: res.data.server || formData.server,
          storage: res.data.storage || formData.storage,
          processing: res.data.processing || formData.processing,
          security: res.data.security || formData.security,
        });
        setFolderPath(res.data.storage?.photo_dir || "");
      }
    } catch (e) {
      console.error("Failed to load settings", e);
    } finally {
      setLoading(false);
    }
  };

  const loadStatus = async () => {
    try {
      const res = await api.get("/management/status");
      setSysStatus(res.data);
    } catch (err) {
      console.error("Failed to load status", err);
    }
  };

  const loadNetworkInfo = async () => {
    try {
      const res = await api.get("/management/network");
      setNetworkInfo(res.data);
    } catch (err) {
      console.error("Failed to load network info", err);
    }
  };

  const handleSave = async (section) => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await api.put("/settings/", { [section]: formData[section] });
      setMessage(
        `${section.charAt(0).toUpperCase() + section.slice(1)} settings saved. Restart may be required.`,
      );
      loadSettings();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("This will delete your configuration. Continue?"))
      return;
    try {
      await api.post("/settings/reset-factory");
      setMessage("Configuration reset. Please restart the server.");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to reset");
    }
  };

  const updateField = (section, field, value) => {
    setFormData((prev) => ({
      ...prev,
      [section]: { ...prev[section], [field]: value },
    }));
  };

  const handleExportConfig = async () => {
    try {
      const res = await api.management.exportConfig();
      downloadBlob(res.data, "homegallery-config.json");
      setMessage("Configuration exported");
    } catch (err) {
      setError(err.response?.data?.detail || "Export failed");
    }
  };

  const handleImportConfig = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.management.importConfig(fd);
      setMessage("Configuration imported. Restart may be required.");
      loadSettings();
    } catch (err) {
      setError(err.response?.data?.detail || "Import failed");
    }
  };

  const handleBackup = async (includePhotos) => {
    setBackupLoading(true);
    setMessage("");
    try {
      const res = await api.management.createBackup(includePhotos);
      const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      downloadBlob(res.data, `homegallery-backup-${ts}.zip`);
      setMessage("Backup downloaded");
    } catch (err) {
      setError(err.response?.data?.detail || "Backup failed");
    } finally {
      setBackupLoading(false);
    }
  };

  const handleRestore = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setRestoreLoading(true);
    setMessage("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.management.restoreBackup(fd);
      setMessage("Backup restored. Restart required for changes.");
      loadStatus();
    } catch (err) {
      setError(err.response?.data?.detail || "Restore failed");
    } finally {
      setRestoreLoading(false);
    }
  };

  const handleWipe = async () => {
    const confirmMap = {
      photos: "DELETE ALL PHOTOS",
      albums: "DELETE ALL ALBUMS",
      database: "WIPE DATABASE",
      full: "WIPE EVERYTHING",
    };
    if (wipeConfirm !== confirmMap[wipeType]) {
      setError(`Please type "${confirmMap[wipeType]}" to confirm`);
      return;
    }
    try {
      const fns = {
        photos: api.management.wipePhotos,
        albums: api.management.wipeAlbums,
        database: api.management.wipeDatabase,
        full: api.management.wipeFull,
      };
      await fns[wipeType](wipeConfirm);
      setMessage(`Successfully wiped ${wipeType}`);
      setWipeConfirm("");
      setWipeType("");
      loadStatus();
    } catch (err) {
      setError(err.response?.data?.detail || "Wipe failed");
    }
  };

  const handleBrowse = async (path) => {
    setBrowseLoading(true);
    try {
      const res = await api.management.browseFolders(path);
      setFolderEntries(res.data.entries);
      setFolderPath(res.data.current_path);
    } catch (err) {
      setError(err.response?.data?.detail || "Browse failed");
    } finally {
      setBrowseLoading(false);
    }
  };

  const handleCreateFolder = async () => {
    const name = prompt("Folder name:");
    if (!name) return;
    try {
      await api.management.createFolder(`${folderPath}/${name}`);
      setMessage("Folder created");
      handleBrowse(folderPath);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create folder");
    }
  };

  const handleDeleteFolder = async (path) => {
    if (!window.confirm(`Delete ${path}? This cannot be undone.`)) return;
    try {
      await api.management.deleteFolder(path, "DELETE FOLDER");
      setMessage("Folder deleted");
      handleBrowse(folderPath);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete folder");
    }
  };

  const handleDbOptimize = async () => {
    try {
      await api.management.optimizeDb();
      setMessage("Database optimized");
      loadStatus();
    } catch (err) {
      setError(err.response?.data?.detail || "Optimization failed");
    }
  };

  const handleDbBackup = async () => {
    try {
      const res = await api.management.backupDb();
      const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      downloadBlob(res.data, `homegallery-db-backup-${ts}.db`);
      setMessage("Database backup downloaded");
    } catch (err) {
      setError(err.response?.data?.detail || "DB backup failed");
    }
  };

  const loadApiKeys = async () => {
    setApiKeysLoading(true);
    try {
      const res = await api.apiKeys.list();
      setApiKeys(res.data);
    } catch (err) {
      console.error("Failed to load API keys", err);
    } finally {
      setApiKeysLoading(false);
    }
  };

  const handleAddApiKey = async () => {
    if (!newKey.name || !newKey.key) {
      setError("Name and key are required");
      return;
    }
    try {
      await api.apiKeys.create(newKey);
      setMessage("API key added");
      setNewKey({ provider: "openai", name: "", key: "" });
      setShowAddKey(false);
      loadApiKeys();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add API key");
    }
  };

  const handleDeleteApiKey = async (id, name) => {
    if (!window.confirm(`Delete API key "${name}"?`)) return;
    try {
      await api.apiKeys.delete(id);
      setMessage("API key deleted");
      loadApiKeys();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete API key");
    }
  };

  const handleToggleKeyActive = async (key) => {
    try {
      await api.apiKeys.update(key.id, { is_active: !key.is_active });
      setMessage(`API key ${key.is_active ? "disabled" : "enabled"}`);
      loadApiKeys();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update API key");
    }
  };

  const loadContactMessages = async () => {
    setContactLoading(true);
    try {
      const res = await api.get("/contact/messages");
      setContactMessages(res.data);
    } catch (err) {
      console.error("Failed to load contact messages", err);
    } finally {
      setContactLoading(false);
    }
  };

  const loadTelegramConfig = async () => {
    try {
      const res = await api.notifications.getTelegram();
      setTelegramConfig(res.data);
    } catch (err) {
      console.error("Failed to load Telegram config", err);
    }
  };

  const saveTelegramConfig = async () => {
    try {
      const res = await api.notifications.updateTelegram(telegramConfig);
      setTelegramConfig(res.data);
      setMessage("Telegram settings saved");
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to save Telegram settings",
      );
    }
  };

  const testTelegramConnection = async () => {
    setTelegramTesting(true);
    setTelegramTestResult(null);
    try {
      const res = await api.notifications.testTelegram();
      setTelegramTestResult(res.data);
    } catch (err) {
      setTelegramTestResult({
        ok: false,
        error: err.response?.data?.detail || "Test failed",
      });
    } finally {
      setTelegramTesting(false);
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await api.put(`/contact/messages/${id}/read`);
      setMessage("Message marked as read");
      loadContactMessages();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update message");
    }
  };

  const handleDeleteMessage = async (id, name) => {
    if (!window.confirm(`Delete message from "${name}"?`)) return;
    try {
      await api.delete(`/contact/messages/${id}`);
      setMessage("Message deleted");
      loadContactMessages();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete message");
    }
  };

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const tabs = [
    { id: "general", label: "General" },
    { id: "storage", label: "Storage & Folders" },
    { id: "database", label: "Database" },
    { id: "backup", label: "Backup & Restore" },
    { id: "wipe", label: "Wipe Data" },
    { id: "agents", label: "Agents" },
    { id: "notifications", label: "Notifications" },
    { id: "api-keys", label: "API Keys" },
    { id: "messages", label: "Messages" },
  ];

  if (loading) return <div className="loading-screen">Loading settings...</div>;
  if (!settings)
    return (
      <div className="empty-settings">
        No configuration found. Run setup first.
      </div>
    );

  const formatSize = (bytes) => {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return `${size.toFixed(1)} ${units[i]}`;
  };

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
        <span className="settings-version">v{settings.version}</span>
      </div>

      {message && <div className="settings-message success">{message}</div>}
      {error && <div className="settings-message error">{error}</div>}

      <div className="settings-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "general" && (
        <div className="settings-grid">
          <SettingSection title="Network" icon="network">
            {networkInfo ? (
              <>
                <div className="network-status">
                  <div className="network-item">
                    <label>Internal Address</label>
                    <code>{networkInfo.internal}</code>
                  </div>
                  <div className="network-item">
                    <label>External Address</label>
                    <code>{networkInfo.external || "Not configured"}</code>
                  </div>
                  <div className="network-item">
                    <label>Server Status</label>
                    <span
                      className={`status-badge ${networkInfo.reachable ? "status-online" : "status-offline"}`}
                    >
                      {networkInfo.reachable ? "Online" : "Offline"}
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <div className="loading">Loading network info...</div>
            )}
          </SettingSection>

          <SettingSection title="Server" icon="server">
            <div className="form-group">
              <label>Host</label>
              <input
                type="text"
                value={formData.server.host}
                onChange={(e) => updateField("server", "host", e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Port</label>
              <input
                type="number"
                value={formData.server.port}
                onChange={(e) =>
                  updateField("server", "port", parseInt(e.target.value))
                }
                min="1"
                max="65535"
              />
            </div>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => handleSave("server")}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </SettingSection>

          <SettingSection title="Processing" icon="gear">
            <div className="form-group toggle-group">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={formData.processing.auto_thumbnails}
                  onChange={(e) =>
                    updateField(
                      "processing",
                      "auto_thumbnails",
                      e.target.checked,
                    )
                  }
                />
                Auto-generate thumbnails
              </label>
            </div>
            <div className="form-group toggle-group">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={formData.processing.face_detection}
                  onChange={(e) =>
                    updateField(
                      "processing",
                      "face_detection",
                      e.target.checked,
                    )
                  }
                />
                Face detection
              </label>
            </div>
            <div className="form-group">
              <label>Face Processing Memory Limit (MB)</label>
              <input
                type="number"
                value={formData.processing.face_processing_max_memory_mb}
                onChange={(e) =>
                  updateField(
                    "processing",
                    "face_processing_max_memory_mb",
                    parseInt(e.target.value),
                  )
                }
              />
            </div>
            <div className="form-group">
              <label>Max Concurrent Tasks</label>
              <input
                type="number"
                value={formData.processing.max_concurrent_tasks}
                onChange={(e) =>
                  updateField(
                    "processing",
                    "max_concurrent_tasks",
                    parseInt(e.target.value),
                  )
                }
                min="1"
                max="8"
              />
            </div>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => handleSave("processing")}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </SettingSection>

          <SettingSection title="Security" icon="shield">
            <div className="form-group">
              <label>JWT Expiration (minutes)</label>
              <input
                type="number"
                value={formData.security.jwt_expire_minutes}
                onChange={(e) =>
                  updateField(
                    "security",
                    "jwt_expire_minutes",
                    parseInt(e.target.value),
                  )
                }
              />
            </div>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => handleSave("security")}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </SettingSection>
        </div>
      )}

      {activeTab === "storage" && (
        <div className="settings-section">
          <SettingSection title="Storage Directories">
            <div className="form-group">
              <label>Photo Directory</label>
              <div className="path-input-group">
                <input
                  type="text"
                  value={formData.storage.photo_dir}
                  onChange={(e) => {
                    updateField("storage", "photo_dir", e.target.value);
                    setFolderPath(e.target.value);
                  }}
                />
                <button
                  className="btn btn-sm"
                  onClick={() => handleBrowse(formData.storage.photo_dir)}
                >
                  Browse
                </button>
              </div>
            </div>
            <div className="form-group">
              <label>Thumbnail Directory</label>
              <input
                type="text"
                value={formData.storage.thumbnail_dir}
                onChange={(e) =>
                  updateField("storage", "thumbnail_dir", e.target.value)
                }
              />
            </div>
            <div className="form-group">
              <label>Face Encoding Directory</label>
              <input
                type="text"
                value={formData.storage.face_encoding_dir}
                onChange={(e) =>
                  updateField("storage", "face_encoding_dir", e.target.value)
                }
              />
            </div>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => handleSave("storage")}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </SettingSection>

          <SettingSection title="Folder Browser">
            <div className="folder-browser">
              <div className="browser-toolbar">
                <button
                  className="btn btn-sm"
                  onClick={() =>
                    folderEntries.length > 0 &&
                    handleBrowse(folderPath.split("/").slice(0, -1).join("/"))
                  }
                >
                  Up
                </button>
                <button className="btn btn-sm" onClick={handleCreateFolder}>
                  New Folder
                </button>
                <span className="browser-path">{folderPath}</span>
              </div>
              {browseLoading && <div className="loading">Loading...</div>}
              <div className="browser-list">
                {folderEntries.map((entry) => (
                  <div
                    key={entry.path}
                    className={`browser-item ${entry.is_directory ? "folder" : "file"}`}
                  >
                    <span className="item-icon">
                      {entry.is_directory ? "📁" : "🖼️"}
                    </span>
                    <span
                      className="item-name"
                      onClick={() =>
                        entry.is_directory && handleBrowse(entry.path)
                      }
                      style={{
                        cursor: entry.is_directory ? "pointer" : "default",
                      }}
                    >
                      {entry.name}
                    </span>
                    <span className="item-size">
                      {!entry.is_directory && formatSize(entry.size)}
                    </span>
                    {entry.is_directory && (
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => handleDeleteFolder(entry.path)}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                ))}
                {folderEntries.length === 0 && !browseLoading && (
                  <div className="empty-browser">Empty directory</div>
                )}
              </div>
            </div>
          </SettingSection>
        </div>
      )}

      {activeTab === "database" && (
        <div className="settings-grid">
          <SettingSection title="Database Status">
            {dbStatus ? (
              <div className="db-stats">
                <div className="stat-item">
                  <span className="stat-label">Type</span>
                  <span className="stat-value">{dbStatus.type}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Size</span>
                  <span className="stat-value">
                    {formatSize(dbStatus.size_bytes)}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Path</span>
                  <span className="stat-value">{dbStatus.path}</span>
                </div>
                {dbStatus.tables &&
                  Object.entries(dbStatus.tables).map(([table, count]) => (
                    <div key={table} className="stat-item">
                      <span className="stat-label">{table}</span>
                      <span className="stat-value">{count} records</span>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="loading">Loading database info...</div>
            )}
          </SettingSection>

          <SettingSection title="Database Actions">
            <div className="action-buttons">
              <button className="btn btn-primary" onClick={handleDbOptimize}>
                Optimize (VACUUM)
              </button>
              <button className="btn btn-primary" onClick={handleDbBackup}>
                Download Backup
              </button>
            </div>
          </SettingSection>
        </div>
      )}

      {activeTab === "backup" && (
        <div className="settings-grid">
          <SettingSection title="Configuration">
            <div className="action-buttons">
              <button className="btn btn-primary" onClick={handleExportConfig}>
                Export Config
              </button>
              <label className="btn btn-primary">
                Import Config
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportConfig}
                  style={{ display: "none" }}
                />
              </label>
            </div>
          </SettingSection>

          <SettingSection title="Full Backup">
            <p>
              Backup includes: configuration, database, thumbnails, and face
              encodings.
            </p>
            <div className="action-buttons">
              <button
                className="btn btn-primary"
                onClick={() => handleBackup(false)}
                disabled={backupLoading}
              >
                {backupLoading ? "Creating..." : "Backup (No Photos)"}
              </button>
              <button
                className="btn btn-primary"
                onClick={() => handleBackup(true)}
                disabled={backupLoading}
              >
                {backupLoading ? "Creating..." : "Backup (Include Photos)"}
              </button>
            </div>
          </SettingSection>

          <SettingSection title="Restore from Backup">
            <p>
              Restore a previously downloaded backup ZIP file. This will
              overwrite current data.
            </p>
            <label className="btn btn-warning">
              {restoreLoading ? "Restoring..." : "Select Backup File"}
              <input
                type="file"
                accept=".zip"
                onChange={handleRestore}
                style={{ display: "none" }}
                disabled={restoreLoading}
              />
            </label>
          </SettingSection>
        </div>
      )}

      {activeTab === "wipe" && (
        <div className="settings-section">
          <SettingSection title="Wipe Data" icon="warning">
            <p className="danger-text">
              These actions cannot be undone. Type the confirmation phrase
              exactly as shown.
            </p>

            <div className="wipe-actions">
              <div className="wipe-item">
                <h4>Wipe All Photos</h4>
                <p>Marks all photos as deleted in the database</p>
                <input
                  type="text"
                  placeholder="DELETE ALL PHOTOS"
                  value={wipeType === "photos" ? wipeConfirm : ""}
                  onChange={(e) => {
                    setWipeType("photos");
                    setWipeConfirm(e.target.value);
                  }}
                />
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleWipe}
                  disabled={wipeType !== "photos" || !wipeConfirm}
                >
                  Wipe Photos
                </button>
              </div>

              <div className="wipe-item">
                <h4>Wipe All Albums</h4>
                <p>Deletes all albums and album-photo associations</p>
                <input
                  type="text"
                  placeholder="DELETE ALL ALBUMS"
                  value={wipeType === "albums" ? wipeConfirm : ""}
                  onChange={(e) => {
                    setWipeType("albums");
                    setWipeConfirm(e.target.value);
                  }}
                />
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleWipe}
                  disabled={wipeType !== "albums" || !wipeConfirm}
                >
                  Wipe Albums
                </button>
              </div>

              <div className="wipe-item">
                <h4>Wipe Database</h4>
                <p>Removes all data except admin user</p>
                <input
                  type="text"
                  placeholder="WIPE DATABASE"
                  value={wipeType === "database" ? wipeConfirm : ""}
                  onChange={(e) => {
                    setWipeType("database");
                    setWipeConfirm(e.target.value);
                  }}
                />
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleWipe}
                  disabled={wipeType !== "database" || !wipeConfirm}
                >
                  Wipe Database
                </button>
              </div>

              <div className="wipe-item">
                <h4>Full System Wipe</h4>
                <p>Deletes everything: photos, thumbnails, database, config</p>
                <input
                  type="text"
                  placeholder="WIPE EVERYTHING"
                  value={wipeType === "full" ? wipeConfirm : ""}
                  onChange={(e) => {
                    setWipeType("full");
                    setWipeConfirm(e.target.value);
                  }}
                />
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleWipe}
                  disabled={wipeType !== "full" || !wipeConfirm}
                >
                  Full Wipe
                </button>
              </div>
            </div>
          </SettingSection>

          <div className="settings-danger-zone">
            <h3>Danger Zone</h3>
            <p>Reset server configuration to factory defaults.</p>
            <button className="btn btn-danger" onClick={handleReset}>
              Reset to Factory Defaults
            </button>
          </div>
        </div>
      )}

      {activeTab === "agents" && (
        <div className="settings-section">
          <SettingSection title="Image Analysis Agents">
            <p className="subtitle">
              Agents run in the background to automatically analyze and enhance
              your photos. All processing happens locally on your device.
            </p>

            {agentsLoading && <div className="loading">Loading agents...</div>}
            {agentsError && (
              <div className="settings-message error">{agentsError}</div>
            )}

            <div className="agents-grid">
              {agents.map((agent) => (
                <AgentCard
                  key={agent.name}
                  agent={agent}
                  onRefresh={fetchAgents}
                />
              ))}
              {agents.length === 0 && !agentsLoading && (
                <div className="empty-agents">
                  <p>
                    No agents registered yet. Agents will appear as they are
                    implemented.
                  </p>
                </div>
              )}
            </div>
          </SettingSection>
        </div>
      )}

      {activeTab === "notifications" && (
        <SettingSection title="Telegram Notifications" icon="bell">
          {telegramConfig ? (
            <>
              <div className="form-group toggle-group">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={telegramConfig.enabled}
                    onChange={(e) =>
                      setTelegramConfig({
                        ...telegramConfig,
                        enabled: e.target.checked,
                      })
                    }
                  />
                  Enabled
                </label>
              </div>

              <div className="form-group">
                <label>Bot Token</label>
                <input
                  type="password"
                  value={telegramConfig.bot_token || ""}
                  onChange={(e) =>
                    setTelegramConfig({
                      ...telegramConfig,
                      bot_token: e.target.value,
                    })
                  }
                  placeholder="Enter new token (leave blank to keep existing)"
                />
                {telegramConfig.bot_token_masked && (
                  <small>Current: {telegramConfig.bot_token_masked}</small>
                )}
              </div>

              <div className="form-group">
                <label>Chat ID</label>
                <input
                  type="text"
                  value={telegramConfig.chat_id || ""}
                  onChange={(e) =>
                    setTelegramConfig({
                      ...telegramConfig,
                      chat_id: e.target.value,
                    })
                  }
                  placeholder="503968467"
                />
              </div>

              <div className="form-group">
                <label>Event Types</label>
                <div className="checkbox-grid">
                  {[
                    "server_start",
                    "server_restart",
                    "error_critical",
                    "security_login_failed",
                    "processing_slow",
                    "agent_duplicates_found",
                  ].map((evt) => (
                    <label key={evt} className="toggle-label">
                      <input
                        type="checkbox"
                        checked={telegramConfig.event_types?.includes(evt)}
                        onChange={(e) => {
                          const events = e.target.checked
                            ? [...(telegramConfig.event_types || []), evt]
                            : (telegramConfig.event_types || []).filter(
                                (x) => x !== evt,
                              );
                          setTelegramConfig({
                            ...telegramConfig,
                            event_types: events,
                          });
                        }}
                      />
                      {evt.replace(/_/g, " ")}
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-actions">
                <button
                  className="btn btn-primary btn-sm"
                  onClick={saveTelegramConfig}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={testTelegramConnection}
                  disabled={telegramTesting}
                >
                  {telegramTesting ? "Testing..." : "Send Test Message"}
                </button>
              </div>

              {telegramTestResult && (
                <div
                  className={`test-result ${telegramTestResult.ok ? "success" : "error"}`}
                >
                  {telegramTestResult.ok
                    ? `✅ ${telegramTestResult.message}`
                    : `❌ ${telegramTestResult.error}`}
                </div>
              )}
            </>
          ) : (
            <div className="loading">Loading...</div>
          )}
        </SettingSection>
      )}

      {activeTab === "api-keys" && (
        <div className="settings-section">
          <SettingSection title="AI Provider API Keys">
            <p className="subtitle">
              Add API keys for external AI providers to enable cloud-based
              analysis. Keys are encrypted before storage. Agents that use cloud
              APIs will only activate when a key is configured.
            </p>

            <div className="api-keys-header">
              <button
                className="btn btn-primary btn-sm"
                onClick={() => setShowAddKey(!showAddKey)}
              >
                {showAddKey ? "Cancel" : "+ Add API Key"}
              </button>
            </div>

            {showAddKey && (
              <div className="api-key-form">
                <div className="form-group">
                  <label>Provider</label>
                  <select
                    value={newKey.provider}
                    onChange={(e) =>
                      setNewKey({ ...newKey, provider: e.target.value })
                    }
                  >
                    {API_PROVIDERS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Primary OpenAI Key"
                    value={newKey.name}
                    onChange={(e) =>
                      setNewKey({ ...newKey, name: e.target.value })
                    }
                  />
                </div>
                <div className="form-group">
                  <label>API Key</label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    value={newKey.key}
                    onChange={(e) =>
                      setNewKey({ ...newKey, key: e.target.value })
                    }
                  />
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleAddApiKey}
                >
                  Save Key
                </button>
              </div>
            )}

            {apiKeysLoading && <div className="loading">Loading keys...</div>}

            <div className="api-keys-list">
              {apiKeys.map((key) => (
                <div key={key.id} className="api-key-item">
                  <div className="api-key-info">
                    <span className="api-key-provider">{key.provider}</span>
                    <span className="api-key-name">{key.name}</span>
                    <span className="api-key-masked">{key.key_masked}</span>
                  </div>
                  <div className="api-key-actions">
                    <span
                      className={`api-key-status ${key.is_active ? "active" : "inactive"}`}
                    >
                      {key.is_active ? "Active" : "Disabled"}
                    </span>
                    <button
                      className="btn btn-sm"
                      onClick={() => handleToggleKeyActive(key)}
                    >
                      {key.is_active ? "Disable" : "Enable"}
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDeleteApiKey(key.id, key.name)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {apiKeys.length === 0 && !apiKeysLoading && (
                <div className="empty-api-keys">
                  <p>
                    No API keys configured. Add a key to enable cloud-based AI
                    analysis.
                  </p>
                </div>
              )}
            </div>
          </SettingSection>
        </div>
      )}

      {activeTab === "messages" && (
        <div className="settings-section">
          <SettingSection title="Contact Messages">
            <p className="subtitle">
              Messages submitted through the contact form.
            </p>

            {contactLoading && (
              <div className="loading">Loading messages...</div>
            )}

            <div className="messages-list">
              {contactMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`message-item ${msg.is_read ? "read" : "unread"}`}
                >
                  <div className="message-header">
                    <div className="message-sender">
                      <span className="message-name">{msg.name}</span>
                      <span className="message-email">{msg.email}</span>
                    </div>
                    <div className="message-meta">
                      <span className="message-date">
                        {new Date(msg.created_at).toLocaleDateString()}
                      </span>
                      {!msg.is_read && (
                        <span className="message-badge">New</span>
                      )}
                    </div>
                  </div>
                  {msg.subject && (
                    <div className="message-subject">{msg.subject}</div>
                  )}
                  <div className="message-body">{msg.message}</div>
                  <div className="message-actions">
                    {!msg.is_read && (
                      <button
                        className="btn btn-sm"
                        onClick={() => handleMarkRead(msg.id)}
                      >
                        Mark Read
                      </button>
                    )}
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDeleteMessage(msg.id, msg.name)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {contactMessages.length === 0 && !contactLoading && (
                <div className="empty-messages">
                  <p>No messages received yet.</p>
                </div>
              )}
            </div>
          </SettingSection>
        </div>
      )}
    </div>
  );
}
