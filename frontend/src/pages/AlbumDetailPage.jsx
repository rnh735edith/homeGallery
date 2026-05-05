import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../services/api'

export default function AlbumDetailPage() {
  const { id } = useParams()
  const [album, setAlbum] = useState(null)
  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.albums.get(id).then((res) => {
      setAlbum(res.data)
      setPhotos(res.data.photos || [])
      setLoading(false)
    })
  }, [id])

  if (loading) return <div className="loading-screen">Loading album...</div>
  if (!album) return <div className="error-screen">Album not found</div>

  return (
    <div className="album-detail-page">
      <div className="album-header">
        <a href="/albums" className="back-link">&larr; Albums</a>
        <h1>{album.name}</h1>
        {album.description && <p className="album-description">{album.description}</p>}
      </div>

      {photos.length === 0 ? (
        <div className="empty-album">
          <p>This album is empty</p>
        </div>
      ) : (
        <div className="photo-grid">
          {photos.map((p) => (
            <div key={p.photo?.id || p.id} className="photo-card">
              <img
                src={`/api/photos/${p.photo?.id || p.id}/thumbnail?size=medium`}
                alt=""
                loading="lazy"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
