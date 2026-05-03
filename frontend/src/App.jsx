import React, { useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import Sidebar from "./components/Layout/Sidebar";
import Header from "./components/Layout/Header";
import SetupPage from "./pages/SetupPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import GalleryPage from "./pages/GalleryPage";
import DashboardPage from "./pages/DashboardPage";
import SettingsPage from "./pages/SettingsPage";
import AlbumsPage from "./pages/AlbumsPage";
import AlbumDetailPage from "./pages/AlbumDetailPage";
import EditorPage from "./pages/EditorPage";
import FacesPage from "./pages/FacesPage";
import DuplicatesPage from "./pages/DuplicatesPage";
import NotFoundPage from "./pages/NotFoundPage";

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function checkSetupStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/setup/status`);
    const data = await res.json();
    return data.is_configured;
  } catch {
    return true;
  }
}

function SetupGuard({ children }) {
  const [isConfigured, setIsConfigured] = useState(null);
  const location = useLocation();

  useEffect(() => {
    checkSetupStatus().then(setIsConfigured);
  }, []);

  if (isConfigured === null) {
    return <div className="loading-screen">Loading...</div>;
  }

  if (!isConfigured && location.pathname !== "/setup") {
    return <Navigate to="/setup" replace />;
  }

  if (isConfigured && location.pathname === "/setup") {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function AppLayout({ children }) {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) {
    return children;
  }
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-main">
        <Header />
        <main className="content-area">{children}</main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <SetupGuard>
      <Routes>
        <Route path="/setup" element={<SetupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout>
                <GalleryPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DashboardPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <AppLayout>
                <SettingsPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/albums"
          element={
            <ProtectedRoute>
              <AppLayout>
                <AlbumsPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/albums/:id"
          element={
            <ProtectedRoute>
              <AppLayout>
                <AlbumDetailPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/editor/:photoId"
          element={
            <ProtectedRoute>
              <AppLayout>
                <EditorPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/faces"
          element={
            <ProtectedRoute>
              <AppLayout>
                <FacesPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/duplicates"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DuplicatesPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route path="/404" element={<NotFoundPage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </SetupGuard>
  );
}
