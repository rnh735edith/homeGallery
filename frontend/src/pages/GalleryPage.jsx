import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useGalleryStore } from "../store/galleryStore";
import MetadataBadge from "../components/Gallery/MetadataBadge";

export default function GalleryPage() {
  const {
    photos,
    loading,
    fetchPhotos,
    toggleFavorite,
    deletePhoto,
    uploadPhoto,
    photoMetadatas,
    fetchMetadataForPhotos,
  } = useGalleryStore();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [showFavorites, setShowFavorites] = useState(false);
  const [selectedPhotos, setSelectedPhotos] = useState([]);
  const [previewPhoto, setPreviewPhoto] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [bulkMoveAlbum, setBulkMoveAlbum] = useState("");
  const [albums, setAlbums] = useState([]);
  const fileInputRef = useRef(null);
  const gridRef = useRef(null);

  useEffect(() => {
    fetchPhotos({
      favorite: showFavorites || undefined,
      q: searchQuery || undefined,
    });
    loadAlbums();
  }, [showFavorites, searchQuery]);

  useEffect(() => {
    const closeContextMenu = () => setContextMenu(null);
    window.addEventListener("click", closeContextMenu);
    return () => window.removeEventListener("click", closeContextMenu);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        setPreviewPhoto(null);
        setContextMenu(null);
        setSelectedPhotos([]);
      }
      if (e.key === "ArrowRight" && previewPhoto) {
        const idx = photos.findIndex((p) => p.id === previewPhoto.id);
        if (idx < photos.length - 1) setPreviewPhoto(photos[idx + 1]);
      }
      if (e.key === "ArrowLeft" && previewPhoto) {
        const idx = photos.findIndex((p) => p.id === previewPhoto.id);
        if (idx > 0) setPreviewPhoto(photos[idx - 1]);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [previewPhoto, photos]);

  useEffect(() => {
    if (photos.length > 0) {
      const ids = photos.map((p) => p.id);
      fetchMetadataForPhotos(ids);
    }
  }, [photos]);

  const loadAlbums = async () => {
    try {
      const api = (await import("../services/api")).default;
      const res = await api.albums.list();
      setAlbums(Array.isArray(res.data) ? res.data : res.data.albums || []);
    } catch (e) {
      console.error("Failed to load albums", e);
    }
  };

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    for (const file of files) {
      try {
        await uploadPhoto(file);
      } catch (err) {
        console.error(`Failed to upload ${file.name}`);
      }
    }
    fetchPhotos({
      favorite: showFavorites || undefined,
      q: searchQuery || undefined,
    });
  };

  const toggleSelect = (id, e) => {
    if (e) e.stopPropagation();
    setSelectedPhotos((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  const handleBulkDelete = async () => {
    if (!window.confirm(`Delete ${selectedPhotos.length} photos?`)) return;
    for (const id of selectedPhotos) {
      await deletePhoto(id);
    }
    setSelectedPhotos([]);
    fetchPhotos({
      favorite: showFavorites || undefined,
      q: searchQuery || undefined,
    });
  };

  const handleBulkAddToAlbum = async () => {
    if (!bulkMoveAlbum) return;
    try {
      const api = (await import("../services/api")).default;
      await api.albums.addPhotos(bulkMoveAlbum, selectedPhotos);
      setSelectedPhotos([]);
      setBulkMoveAlbum("");
    } catch (err) {
      console.error("Failed to add to album", err);
    }
  };

  const handleContextMenu = (photo, e) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ photo, x: e.clientX, y: e.clientY });
  };

  const handlePhotoAction = async (action, photo) => {
    setContextMenu(null);
    switch (action) {
      case "preview":
        setPreviewPhoto(photo);
        break;
      case "edit":
        navigate(`/editor/${photo.id}`);
        break;
      case "delete":
        if (window.confirm(`Delete "${photo.filename}"?`)) {
          await deletePhoto(photo.id);
          fetchPhotos({
            favorite: showFavorites || undefined,
            q: searchQuery || undefined,
          });
        }
        break;
      case "download":
        const a = document.createElement("a");
        a.href = `/api/photos/${photo.id}/full`;
        a.download = photo.filename;
        a.click();
        break;
      case "toggle-fav":
        await toggleFavorite(photo.id);
        break;
      default:
        break;
    }
  };

  return (
    <div className="gallery-page">
      <div className="gallery-toolbar">
        <div className="toolbar-left">
          <input
            type="search"
            placeholder="Search photos..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <button
            className={`btn btn-sm ${showFavorites ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setShowFavorites(!showFavorites)}
          >
            {showFavorites ? "\u2605 Favorites" : "\u2606 Favorites"}
          </button>
        </div>
        <div className="toolbar-right">
          {selectedPhotos.length > 0 && (
            <>
              <button
                className="btn btn-danger btn-sm"
                onClick={handleBulkDelete}
              >
                Delete ({selectedPhotos.length})
              </button>
              <select
                value={bulkMoveAlbum}
                onChange={(e) => setBulkMoveAlbum(e.target.value)}
                className="album-select"
              >
                <option value="">Add to album...</option>
                {albums.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              {bulkMoveAlbum && (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleBulkAddToAlbum}
                >
                  Add to Album
                </button>
              )}
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setSelectedPhotos([])}
              >
                Clear
              </button>
            </>
          )}
          <button
            className="btn btn-primary btn-sm"
            onClick={() => fileInputRef.current?.click()}
          >
            Upload
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            hidden
            onChange={handleFileSelect}
          />
        </div>
      </div>

      {loading ? (
        <div className="loading-grid">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="photo-card loading" />
          ))}
        </div>
      ) : photos.length === 0 ? (
        <div className="empty-gallery">
          <div className="empty-icon">📷</div>
          <h2>No photos yet</h2>
          <p>Upload your first photos to get started</p>
          <button
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
          >
            Upload Photos
          </button>
        </div>
      ) : (
        <div className="photo-grid" ref={gridRef}>
          {photos.map((photo) => (
            <div
              key={photo.id}
              className={`photo-card ${selectedPhotos.includes(photo.id) ? "selected" : ""}`}
              onClick={() => toggleSelect(photo.id)}
              onDoubleClick={() => handlePhotoAction("preview", photo)}
              onContextMenu={(e) => handleContextMenu(photo, e)}
            >
              <img
                src={
                  photo.thumbnail_paths?.medium ||
                  `/api/photos/${photo.id}/thumbnail?size=medium`
                }
                alt={photo.filename}
                loading="lazy"
              />
              {photoMetadatas[photo.id] && (
                <MetadataBadge metadata={photoMetadatas[photo.id]} compact />
              )}
              <div className="photo-overlay">
                <button
                  className={`favorite-btn ${photo.favorite ? "active" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFavorite(photo.id);
                  }}
                >
                  {photo.favorite ? "\u2605" : "\u2606"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {contextMenu && (
        <div
          className="context-menu"
          style={{ top: contextMenu.y, left: contextMenu.x }}
        >
          <button
            className="context-item"
            onClick={() => handlePhotoAction("preview", contextMenu.photo)}
          >
            <span className="context-icon">🔍</span> Preview
          </button>
          <button
            className="context-item"
            onClick={() => handlePhotoAction("edit", contextMenu.photo)}
          >
            <span className="context-icon">✏️</span> Edit
          </button>
          <button
            className="context-item"
            onClick={() => handlePhotoAction("download", contextMenu.photo)}
          >
            <span className="context-icon">📥</span> Download
          </button>
          <button
            className="context-item"
            onClick={() => handlePhotoAction("toggle-fav", contextMenu.photo)}
          >
            <span className="context-icon">
              {contextMenu.photo.favorite ? "☆" : "★"}
            </span>
            {contextMenu.photo.favorite ? "Remove Favorite" : "Add Favorite"}
          </button>
          <div className="context-divider" />
          <button
            className="context-item danger"
            onClick={() => handlePhotoAction("delete", contextMenu.photo)}
          >
            <span className="context-icon">🗑️</span> Delete
          </button>
        </div>
      )}

      {previewPhoto && (
        <div className="lightbox" onClick={() => setPreviewPhoto(null)}>
          <div
            className="lightbox-content"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="lightbox-close"
              onClick={() => setPreviewPhoto(null)}
            >
              &times;
            </button>
            <button
              className="lightbox-nav prev"
              onClick={() => {
                const idx = photos.findIndex((p) => p.id === previewPhoto.id);
                if (idx > 0) setPreviewPhoto(photos[idx - 1]);
              }}
            >
              &#8249;
            </button>
            <button
              className="lightbox-nav next"
              onClick={() => {
                const idx = photos.findIndex((p) => p.id === previewPhoto.id);
                if (idx < photos.length - 1) setPreviewPhoto(photos[idx + 1]);
              }}
            >
              &#8250;
            </button>
            <img
              src={`/api/photos/${previewPhoto.id}/full`}
              alt={previewPhoto.filename}
            />
            <div className="lightbox-info">
              <span>{previewPhoto.filename}</span>
              <div className="lightbox-actions">
                <button
                  className="btn btn-sm"
                  onClick={() => navigate(`/editor/${previewPhoto.id}`)}
                >
                  Edit
                </button>
                <button
                  className="btn btn-sm"
                  onClick={() => handlePhotoAction("download", previewPhoto)}
                >
                  Download
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handlePhotoAction("delete", previewPhoto)}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
