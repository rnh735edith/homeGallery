export default function MetadataBadge({ metadata, compact = false }) {
  if (!metadata) return null;

  const { scene_type, objects, colors, sharpness } = metadata;

  if (compact) {
    return (
      <div className="metadata-badge-compact">
        {scene_type && (
          <span className="badge badge-scene" title={scene_type}>
            {getSceneIcon(scene_type)} {scene_type}
          </span>
        )}
        {sharpness !== null && sharpness !== undefined && (
          <span
            className={`badge badge-quality ${sharpness > 0.7 ? "good" : sharpness > 0.4 ? "medium" : "low"}`}
            title={`Sharpness: ${Math.round(sharpness * 100)}%`}
          >
            {Math.round(sharpness * 100)}%
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="metadata-badge">
      {scene_type && (
        <div className="metadata-section">
          <h4>Scene</h4>
          <span className="badge badge-scene">
            {getSceneIcon(scene_type)} {scene_type}
          </span>
        </div>
      )}

      {objects && objects.length > 0 && (
        <div className="metadata-section">
          <h4>Objects</h4>
          <div className="tag-list">
            {objects.map((obj, i) => (
              <span key={i} className="badge badge-tag">
                {obj}
              </span>
            ))}
          </div>
        </div>
      )}

      {colors && colors.length > 0 && (
        <div className="metadata-section">
          <h4>Dominant Colors</h4>
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
