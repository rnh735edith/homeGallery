import { useEffect, useState } from "react";
import api from "../services/api";

export default function DuplicatesPage() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDuplicates();
  }, []);

  const loadDuplicates = async () => {
    try {
      const res = await api.photos.getDuplicates();
      setGroups(res.data.groups || []);
    } catch (err) {
      console.error("Failed to load duplicates:", err);
    } finally {
      setLoading(false);
    }
  };

  const getThumbUrl = (photo) => {
    const thumbs = photo.thumbnail_paths || {};
    if (thumbs.small) return thumbs.small;
    if (thumbs.medium) return thumbs.medium;
    return `/api/photos/${photo.id}/thumbnail/small`;
  };

  if (loading) {
    return <div className="loading-screen">Loading duplicates...</div>;
  }

  if (groups.length === 0) {
    return (
      <div className="duplicates-page">
        <h1>Duplicate Photos</h1>
        <div className="empty-duplicates">
          <div className="empty-icon">✨</div>
          <h2>No duplicates found</h2>
          <p>Your photo collection is clean!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="duplicates-page">
      <h1>Duplicate Photos</h1>
      <p className="duplicates-summary">
        Found {groups.length} groups with{" "}
        {groups.reduce((sum, g) => sum + (g.duplicates?.length || 0), 0)}{" "}
        duplicate photos
      </p>

      <div className="duplicate-groups">
        {groups.map((group, idx) => (
          <div key={idx} className="duplicate-group">
            <div className="duplicate-original">
              <div className="duplicate-badge badge-original">Original</div>
              <img
                src={getThumbUrl(group.original)}
                alt={group.original.filename}
              />
              <p className="duplicate-filename">{group.original.filename}</p>
            </div>

            <div className="duplicate-copies">
              {group.duplicates?.map((dup) => (
                <div key={dup.id} className="duplicate-copy">
                  <div className="duplicate-badge badge-duplicate">
                    Duplicate
                  </div>
                  <img src={getThumbUrl(dup)} alt={dup.filename} />
                  <p className="duplicate-filename">{dup.filename}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
