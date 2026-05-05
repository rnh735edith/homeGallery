import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import StepPhotoDir from "../components/Setup/StepPhotoDir";
import StepAdmin from "../components/Setup/StepAdmin";
import StepServer from "../components/Setup/StepServer";
import StepDatabase from "../components/Setup/StepDatabase";
import StepProcessing from "../components/Setup/StepProcessing";
import StepNotifications from "../components/Setup/StepNotifications";
import StepSummary from "../components/Setup/StepSummary";

const STEPS = [
  { id: "storage", label: "Photo Library", component: StepPhotoDir },
  { id: "admin", label: "Admin Account", component: StepAdmin },
  { id: "server", label: "Server", component: StepServer },
  { id: "database", label: "Database", component: StepDatabase },
  { id: "processing", label: "Processing", component: StepProcessing },
  { id: "notifications", label: "Notifications", component: StepNotifications },
  { id: "summary", label: "Review", component: StepSummary },
];

export default function SetupPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [config, setConfig] = useState({
    storage: {
      photo_dir: "./data/photos",
      thumbnail_dir: "./data/thumbnails",
      face_encoding_dir: "./data/face_encodings",
    },
    admin: { username: "admin", password: "", confirmPassword: "" },
    server: { host: "0.0.0.0", port: 8080 },
    database: { type: "sqlite", url: "sqlite:///./data/gallery.db" },
    processing: {
      auto_thumbnails: true,
      face_detection: true,
      thumbnail_sizes: { small: 200, medium: 800, large: 1920 },
    },
    notifications: { enabled: false, bot_token: "", chat_id: "" },
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const updateConfig = (section, values) => {
    setConfig((prev) => ({
      ...prev,
      [section]: { ...prev[section], ...values },
    }));
  };

  const handleNext = () => {
    setError("");
    const step = STEPS[currentStep];

    if (step.id === "admin") {
      if (!config.admin.username || config.admin.username.length < 3) {
        setError("Username must be at least 3 characters");
        return;
      }
      if (config.admin.password !== config.admin.confirmPassword) {
        setError("Passwords do not match");
        return;
      }
      if (config.admin.password.length < 6) {
        setError("Password must be at least 6 characters");
        return;
      }
    }

    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    setError("");
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const { admin, ...rest } = config;
      await api.setup.configure({
        ...rest,
        admin: { username: admin.username, password: admin.password },
      });
      window.location.href = "/login";
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save configuration");
    } finally {
      setLoading(false);
    }
  };

  const StepComponent = STEPS[currentStep].component;
  const progress = ((currentStep + 1) / STEPS.length) * 100;

  return (
    <div className="setup-page">
      <div className="setup-container">
        <div className="setup-header">
          <h1>HomeGallery Setup</h1>
          <div className="setup-progress">
            <div
              className="setup-progress-bar"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="setup-step-label">
            Step {currentStep + 1} of {STEPS.length}
          </p>
        </div>

        <div className="setup-content">
          {error && <div className="setup-error">{error}</div>}
          <StepComponent config={config} updateConfig={updateConfig} />
        </div>

        <div className="setup-footer">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className="btn btn-secondary"
          >
            Back
          </button>
          {currentStep < STEPS.length - 1 ? (
            <button onClick={handleNext} className="btn btn-primary">
              Next
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? "Saving..." : "Save & Start"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
