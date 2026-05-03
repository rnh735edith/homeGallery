import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGalleryStore } from "../store/galleryStore";
import api from "../services/api";
import AlbumCard from "../components/Albums/AlbumCard";

export default function AlbumsPage() {
  const { albums, fetchAlbums } = useGalleryStore();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
  const [newAlbum, setNewAlbum] = useState({ name: "", description: "" });

  useEffect(() => {
    fetchAlbums();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.albums.create(newAlbum);
      setShowCreate(false);
      setNewAlbum({ name: "", description: "" });
      await fetchAlbums();
    } catch (err) {
      console.error("Failed to create album:", err);
    }
  };

  const handleDelete = async (id) => {
    await fetchAlbums();
  };

  const handleEdit = (album) => {
    console.log("Edit album:", album);
  };

  const handleClick = (album) => {
    navigate(`/albums/${album.id}`);
  };

  const userAlbums = albums.filter((a) => !a.is_auto);
  const autoAlbums = albums.filter((a) => a.is_auto);

  return (
    <div className="albums-page">
      <div className="albums-toolbar">
        <h1>Albums</h1>
        <button
          className="btn btn-primary"
          data-testid="create-album"
          onClick={() => setShowCreate(true)}
        >
          + New Album
        </button>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Album</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  name="album-name"
                  value={newAlbum.name}
                  onChange={(e) =>
                    setNewAlbum({ ...newAlbum, name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  name="album-description"
                  value={newAlbum.description}
                  onChange={(e) =>
                    setNewAlbum({ ...newAlbum, description: e.target.value })
                  }
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {albums.length === 0 ? (
        <div className="empty-albums">
          <div className="empty-icon">📁</div>
          <h2>No albums yet</h2>
          <p>Create your first album to organize photos</p>
        </div>
      ) : (
        <>
          {userAlbums.length > 0 && (
            <>
              <h2 className="albums-section-header">Your Albums</h2>
              <div className="album-grid">
                {userAlbums.map((album) => (
                  <AlbumCard
                    key={album.id}
                    album={album}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onClick={handleClick}
                  />
                ))}
              </div>
            </>
          )}

          {autoAlbums.length > 0 && (
            <>
              <h2 className="albums-section-header">Auto-Albums</h2>
              <div className="album-grid">
                {autoAlbums.map((album) => (
                  <AlbumCard
                    key={album.id}
                    album={album}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onClick={handleClick}
                  />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
