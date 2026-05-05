import { useEffect, useState } from 'react'
import api from '../services/api'

export default function FacesPage() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.faces.persons().then((res) => {
      setPersons(res.data.persons || res.data || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading-screen">Loading faces...</div>

  return (
    <div className="faces-page">
      <h1>Faces</h1>

      {persons.length === 0 ? (
        <div className="empty-faces">
          <div className="empty-icon">👤</div>
          <h2>No faces detected yet</h2>
          <p>Face detection runs in the background after photos are uploaded</p>
        </div>
      ) : (
        <div className="person-grid">
          {persons.map((person) => (
            <div key={person.id} className="person-card">
              <div className="person-face">
                <span className="face-placeholder">👤</span>
              </div>
              <div className="person-info">
                <h3>{person.name || 'Unknown'}</h3>
                <p>{person.photo_count || 0} photos</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
