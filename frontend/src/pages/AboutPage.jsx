import { Link } from "react-router-dom";

export default function AboutPage() {
  return (
    <div className="about-page">
      <div className="about-container">
        <div className="about-header">
          <h1>HomeGallery</h1>
          <p className="about-tagline">
            Your personal photo gallery, powered by AI
          </p>
        </div>

        <div className="about-section">
          <h2>About This Project</h2>
          <p>
            HomeGallery is a standalone, lightweight home image processing
            server with intelligent features like face recognition,
            auto-organization, content analysis, and visual search — all running
            locally without external API dependencies.
          </p>
        </div>

        <div className="about-section">
          <h2>Features</h2>
          <ul className="feature-list">
            <li>Smart photo gallery with grid and list views</li>
            <li>Album creation and management</li>
            <li>Face detection and recognition</li>
            <li>Duplicate photo detection (pHash)</li>
            <li>Photo editor with basic adjustments</li>
            <li>Content analysis (quality, sharpness, composition)</li>
            <li>Enhancement suggestions based on scene type</li>
            <li>Visual and text-based search</li>
            <li>Auto-organization by date and location</li>
            <li>Dashboard with statistics and metrics</li>
          </ul>
        </div>

        <div className="about-section">
          <h2>Tech Stack</h2>
          <div className="tech-grid">
            <div className="tech-item">
              <h3>Backend</h3>
              <p>FastAPI (Python 3.10+)</p>
            </div>
            <div className="tech-item">
              <h3>Frontend</h3>
              <p>React 18 + Vite + Zustand</p>
            </div>
            <div className="tech-item">
              <h3>Database</h3>
              <p>SQLite (PostgreSQL supported)</p>
            </div>
            <div className="tech-item">
              <h3>Workers</h3>
              <p>APScheduler background jobs</p>
            </div>
          </div>
        </div>

        <div className="about-section">
          <h2>AI Agents</h2>
          <p>
            HomeGallery uses autonomous agents to analyze and organize your
            photos:
          </p>
          <ul className="agent-list">
            <li>
              <strong>Metadata Agent</strong> — Extracts EXIF data, detects
              objects, colors, and tags
            </li>
            <li>
              <strong>Organization Agent</strong> — Auto-creates albums by date
              and location
            </li>
            <li>
              <strong>Enhancement Agent</strong> — Suggests improvements based
              on scene type
            </li>
            <li>
              <strong>Analysis Agent</strong> — Scores photos on quality,
              sharpness, and composition
            </li>
            <li>
              <strong>Search Agent</strong> — Enables visual similarity and
              text-based search
            </li>
          </ul>
        </div>

        <div className="about-footer">
          <p>
            Have a question or feedback?{" "}
            <Link to="/contact" className="about-link">
              Contact us
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
