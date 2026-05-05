import { useState } from "react";
import api from "../../services/api";

export default function EnhanceButton({ photoId, onEnhanced }) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleEnhance = async (e) => {
    e.stopPropagation();
    if (loading) return;

    setLoading(true);
    try {
      await api.analysis.applyEnhancement(photoId);
      setSuccess(true);
      setLoading(false);
      if (onEnhanced) onEnhanced(photoId);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to enhance photo:", err);
      setLoading(false);
    }
  };

  if (success) {
    return (
      <button className="enhance-btn success" disabled>
        ✓
      </button>
    );
  }

  return (
    <button
      className={`enhance-btn ${loading ? "loading" : ""}`}
      onClick={handleEnhance}
      disabled={loading}
      title="Enhance photo"
    >
      {loading ? "..." : "✨"}
    </button>
  );
}
