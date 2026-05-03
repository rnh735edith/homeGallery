import { useState } from "react";
import api from "../../services/api";

export default function AlbumCard({ album, onEdit, onDelete, onClick }) {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleDelete = (e) => {
    e.stopPropagation();
    e.preventDefault();
    if (album.is_auto) return;
    setShowConfirm(true);
  };

  const confirmDelete = async () => {
    try {
      await api.albums.delete(album.id);
      onDelete?.(album.id);
      setShowConfirm(false);
    } catch (err) {
      console.error("Failed to delete album:", err);
    }
  };

  const handleEdit = (e) => {
    e.stopPropagation();
    e.preventDefault();
    if (album.is_auto) return;
    onEdit?.(album);
  };

  return (
    <>
      <div
        className={`album-card ${album.is_auto ? "album-card-auto" : ""}`}
        onClick={() => onClick?.(album)}
      >
        <div className="album-cover">
          <span className="album-placeholder">📁</span>
          {album.is_auto && <span className="badge badge-auto">Auto</span>}
        </div>
        <div className="album-info">
          <h3>{album.name}</h3>
          <p className="album-count">{album.photo_count || 0} photos</p>
          <div className="album-actions">
            <button
              className="btn btn-sm btn-ghost"
              onClick={handleEdit}
              disabled={album.is_auto}
              title={
                album.is_auto
                  ? "Auto-generated albums cannot be modified"
                  : "Edit"
              }
            >
              Edit
            </button>
            <button
              className="btn btn-sm btn-danger"
              onClick={handleDelete}
              disabled={album.is_auto}
              title={
                album.is_auto
                  ? "Auto-generated albums cannot be deleted"
                  : "Delete"
              }
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Album</h2>
            <p>Are you sure you want to delete &quot;{album.name}&quot;?</p>
            <div className="modal-actions">
              <button
                className="btn btn-ghost"
                onClick={() => setShowConfirm(false)}
              >
                Cancel
              </button>
              <button className="btn btn-danger" onClick={confirmDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
