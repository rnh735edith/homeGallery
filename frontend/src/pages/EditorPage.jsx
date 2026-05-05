import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

export default function EditorPage() {
  const { photoId } = useParams();
  const navigate = useNavigate();
  const [photo, setPhoto] = useState(null);
  const [adjustments, setAdjustments] = useState({
    brightness: 0,
    contrast: 0,
    saturation: 0,
    exposure: 0,
  });
  const [rotation, setRotation] = useState(0);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.photos
      .get(photoId)
      .then((res) => {
        setPhoto(res.data);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [photoId]);

  const updateAdjustment = (key, value) => {
    setAdjustments((prev) => ({ ...prev, [key]: parseInt(value) }));
  };

  const handleRotate = (deg) => setRotation((prev) => (prev + deg) % 360);
  const handleFlipH = () => setFlipH((prev) => !prev);
  const handleFlipV = () => setFlipV((prev) => !prev);

  const handleReset = () => {
    setAdjustments({ brightness: 0, contrast: 0, saturation: 0, exposure: 0 });
    setRotation(0);
    setFlipH(false);
    setFlipV(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.photos.update(photoId, {
        adjustments,
        rotation,
        flip_h: flipH,
        flip_v: flipV,
      });
      navigate("/");
    } catch (err) {
      console.error("Failed to save edits:", err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading-screen">Loading photo...</div>;
  if (!photo) return <div className="error-screen">Photo not found</div>;

  const filterStyle = {
    brightness: `${100 + adjustments.brightness}%`,
    contrast: `${100 + adjustments.contrast}%`,
    saturate: `${100 + adjustments.saturation}%`,
  };

  const transformStyle = {
    transform: `rotate(${rotation}deg) scaleX(${flipH ? -1 : 1}) scaleY(${flipV ? -1 : 1})`,
    filter: `brightness(${filterStyle.brightness}) contrast(${filterStyle.contrast}) saturate(${filterStyle.saturate})`,
  };

  return (
    <div className="editor-page">
      <div className="editor-header">
        <button className="btn btn-ghost" onClick={() => navigate("/")}>
          &larr; Back
        </button>
        <h2>Edit: {photo.filename}</h2>
        <div className="editor-actions">
          <button className="btn btn-ghost" onClick={handleReset}>
            Reset
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      <div className="editor-content">
        <div className="editor-canvas">
          <img
            src={`/api/photos/${photoId}/full`}
            alt={photo.filename}
            style={transformStyle}
          />
        </div>

        <div className="editor-controls">
          <div className="control-section">
            <h3>Transform</h3>
            <div className="transform-buttons">
              <button className="btn btn-sm" onClick={() => handleRotate(90)}>
                Rotate 90&deg;
              </button>
              <button className="btn btn-sm" onClick={() => handleRotate(-90)}>
                Rotate -90&deg;
              </button>
              <button className="btn btn-sm" onClick={handleFlipH}>
                Flip H
              </button>
              <button className="btn btn-sm" onClick={handleFlipV}>
                Flip V
              </button>
            </div>
          </div>

          <div className="control-section">
            <h3>Adjustments</h3>
            {Object.entries(adjustments).map(([key, value]) => (
              <div key={key} className="adjustment-control">
                <label>{key.charAt(0).toUpperCase() + key.slice(1)}</label>
                <input
                  type="range"
                  min="-100"
                  max="100"
                  value={value}
                  onChange={(e) => updateAdjustment(key, e.target.value)}
                />
                <span className="adjustment-value">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
