import { useState } from "react";

export default function PhotoMetadataPanel({ metadata, onClose }) {
  if (!metadata) return null;

  const [showExif, setShowExif] = useState(false);
  const {
    objects,
    colors,
    scene_type,
    tags,
    sharpness,
    brightness,
    quality_score,
  } = metadata;

  return (
    <div className="metadata-panel">
      <div className="metadata-panel-header">
        <h3>Photo Metadata</h3>
        <button className="btn btn-ghost btn-sm" onClick={onClose}>
          &times;
        </button>
      </div>

      <div className="metadata-panel-body">
        {scene_type && (
          <div className="metadata-field">
            <label>Scene</label>
            <span className="badge badge-scene">
              {getSceneIcon(scene_type)} {scene_type}
            </span>
          </div>
        )}

        {objects && objects.length > 0 && (
          <div className="metadata-field">
            <label>Objects</label>
            <div className="tag-list">
              {objects.map((obj, i) => (
                <span key={i} className="badge badge-tag">
                  {obj}
                </span>
              ))}
            </div>
          </div>
        )}

        {tags && tags.length > 0 && (
          <div className="metadata-field">
            <label>Tags</label>
            <div className="tag-list">
              {tags.map((tag, i) => (
                <span key={i} className="badge badge-tag">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {colors && colors.length > 0 && (
          <div className="metadata-field">
            <label>Dominant Colors</label>
            <div className="color-palette">
              {colors.map((color, i) => (
                <div
                  key={i}
                  className="color-swatch"
                  style={{ backgroundColor: color }}
                  title={color}
                />
              ))}
            </div>
          </div>
        )}

        {(sharpness !== null ||
          brightness !== null ||
          quality_score !== null) && (
          <div className="metadata-field">
            <label>Quality Metrics</label>
            <div className="metrics-grid">
              {sharpness !== null && (
                <MetricBar label="Sharpness" value={sharpness} />
              )}
              {brightness !== null && (
                <MetricBar label="Brightness" value={brightness} />
              )}
              {quality_score !== null && (
                <MetricBar label="Quality" value={quality_score} />
              )}
            </div>
          </div>
        )}

        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setShowExif(!showExif)}
        >
          {showExif ? "Hide" : "Show"} EXIF Data
        </button>

        {showExif && metadata.exif && (
          <div className="exif-data">
            {Object.entries(metadata.exif).map(([key, value]) => (
              <div key={key} className="exif-row">
                <span className="exif-key">{key}</span>
                <span className="exif-value">{value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MetricBar({ label, value }) {
  const percentage = Math.round(value * 100);
  return (
    <div className="metric-bar">
      <span className="metric-label">{label}</span>
      <div className="metric-track">
        <div
          className={`metric-fill ${percentage > 70 ? "good" : percentage > 40 ? "medium" : "low"}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="metric-value">{percentage}%</span>
    </div>
  );
}

function getSceneIcon(sceneType) {
  const icons = {
    outdoor: "🌳",
    indoor: "🏠",
    night: "🌙",
    morning: "🌅",
    evening: "🌇",
    daytime: "☀️",
    beach: "🏖️",
    mountain: "⛰️",
    general: "📷",
    gps: "📍",
    panoramic: "🌐",
    vertical: "📱",
    zoom: "🔍",
  };
  return icons[sceneType] || "📷";
}
