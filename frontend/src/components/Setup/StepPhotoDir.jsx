export default function StepPhotoDir({ config, updateConfig }) {
  return (
    <div className="setup-step">
      <h2>Photo Library</h2>
      <p>Where are your photos stored? You can change this later by editing the config file.</p>
      <div className="form-group">
        <label htmlFor="photo-dir">Photo Directory</label>
        <input
          id="photo-dir"
          type="text"
          value={config.storage.photo_dir}
          onChange={(e) => updateConfig('storage', { photo_dir: e.target.value })}
          placeholder="./data/photos"
        />
        <small className="form-hint">Absolute or relative path to your photo collection</small>
      </div>
      <div className="form-group">
        <label htmlFor="thumbnail-dir">Thumbnail Directory</label>
        <input
          id="thumbnail-dir"
          type="text"
          value={config.storage.thumbnail_dir}
          onChange={(e) => updateConfig('storage', { thumbnail_dir: e.target.value })}
          placeholder="./data/thumbnails"
        />
      </div>
      <div className="form-group">
        <label htmlFor="face-dir">Face Encoding Directory</label>
        <input
          id="face-dir"
          type="text"
          value={config.storage.face_encoding_dir}
          onChange={(e) => updateConfig('storage', { face_encoding_dir: e.target.value })}
          placeholder="./data/face_encodings"
        />
      </div>
    </div>
  )
}
