import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem("refreshToken");
        if (refreshToken) {
          const response = await axios.post("/api/auth/refresh", {
            refreshToken,
          });
          const { token, refreshToken: newRefreshToken } = response.data;
          localStorage.setItem("token", token);
          if (newRefreshToken) {
            localStorage.setItem("refreshToken", newRefreshToken);
          }
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export const auth = {
  login: (credentials) => api.post("/auth/login", credentials),
  register: (userData) => api.post("/auth/register", userData),
  me: () => api.get("/auth/me"),
  changePassword: (data) => api.put("/auth/password", data),
};

export const photos = {
  list: (params) => api.get("/photos", { params }),
  get: (id) => api.get(`/photos/${id}`),
  upload: (formData, onProgress) =>
    api.post("/photos/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    }),
  update: (id, data) => api.put(`/photos/${id}`, data),
  delete: (id) => api.delete(`/photos/${id}`),
  deleteBulk: (ids) => api.post("/photos/delete-bulk", { ids }),
  thumbnail: (id, size = "medium") =>
    `/api/photos/${id}/thumbnail?size=${size}`,
  fullImage: (id) => `/api/photos/${id}/full`,
  toggleFavorite: (id) => api.post(`/photos/${id}/favorite`),
  download: (id) => api.get(`/photos/${id}/download`, { responseType: "blob" }),
};

export const albums = {
  list: (params) => api.get("/albums", { params }),
  get: (id) => api.get(`/albums/${id}`),
  create: (data) => api.post("/albums", data),
  update: (id, data) => api.put(`/albums/${id}`, data),
  delete: (id) => api.delete(`/albums/${id}`),
  addPhotos: (id, photoIds) => api.post(`/albums/${id}/photos`, { photoIds }),
  removePhotos: (id, photoIds) =>
    api.delete(`/albums/${id}/photos`, { data: { photoIds } }),
  reorderPhotos: (id, photoIds) =>
    api.put(`/albums/${id}/photos/reorder`, { photoIds }),
};

export const faces = {
  persons: (params) => api.get("/faces/persons", { params }),
  updatePerson: (id, data) => api.put(`/faces/persons/${id}`, data),
  mergePersons: (sourceId, targetId) =>
    api.post(`/faces/persons/${sourceId}/merge`, { targetId }),
  photoFaces: (photoId) => api.get(`/faces/photos/${photoId}`),
  assignFace: (faceId, personId) =>
    api.post(`/faces/faces/${faceId}/assign`, { personId }),
  unassignFace: (faceId) => api.delete(`/faces/faces/${faceId}/assign`),
  deletePerson: (id) => api.delete(`/faces/persons/${id}`),
};

export const search = {
  search: (query, params) =>
    api.get("/search", { params: { q: query, ...params } }),
  memories: () => api.get("/search/memories"),
};

export const settings = {
  getSettings: () => api.get("/settings"),
  updateSettings: (data) => api.put("/settings", data),
  generateThumbnails: () => api.post("/settings/thumbnails/generate"),
  clearCache: () => api.post("/settings/cache/clear"),
  scanDirectory: () => api.post("/settings/scan"),
  backup: () => api.get("/settings/backup", { responseType: "blob" }),
  restore: (formData) =>
    api.post("/settings/restore", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
};

export const setup = {
  getStatus: () => api.get("/setup/status"),
  configure: (data) => api.post("/setup/configure", data),
  reset: () => api.post("/setup/reset"),
};

export const management = {
  getStatus: () => api.get("/management/status"),
  exportConfig: () =>
    api.get("/management/config/export", { responseType: "blob" }),
  importConfig: (formData) =>
    api.post("/management/config/import", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  createBackup: (includePhotos = false) =>
    api.get(`/management/backup/full?include_photos=${includePhotos}`, {
      responseType: "blob",
    }),
  restoreBackup: (formData) =>
    api.post("/management/backup/restore", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  wipePhotos: (confirm) =>
    api.post(`/management/wipe/photos?confirm=${encodeURIComponent(confirm)}`),
  wipeAlbums: (confirm) =>
    api.post(`/management/wipe/albums?confirm=${encodeURIComponent(confirm)}`),
  wipeDatabase: (confirm) =>
    api.post(
      `/management/wipe/database?confirm=${encodeURIComponent(confirm)}`,
    ),
  wipeFull: (confirm) =>
    api.post(`/management/wipe/full?confirm=${encodeURIComponent(confirm)}`),
  browseFolders: (path) =>
    api.get("/management/folders/browse", { params: { path } }),
  createFolder: (path) =>
    api.post("/management/folders/create", null, { params: { path } }),
  deleteFolder: (path, confirm) =>
    api.post(
      `/management/folders/delete?path=${encodeURIComponent(path)}&confirm=${encodeURIComponent(confirm)}`,
    ),
  getDbStatus: () => api.get("/management/db/status"),
  optimizeDb: () => api.post("/management/db/optimize"),
  backupDb: () => api.get("/management/db/backup", { responseType: "blob" }),
};

export const agents = {
  getStatus: () => api.get("/agents/status"),
  getAgentStatus: (name) => api.get(`/agents/${name}/status`),
  startAgent: (name) => api.post(`/agents/${name}/start`),
  stopAgent: (name) => api.post(`/agents/${name}/stop`),
  runAgent: (name) => api.post(`/agents/${name}/run`),
  resetAgent: (name) => api.post(`/agents/${name}/reset`),
};

const apiClient = api;
apiClient.auth = auth;
apiClient.photos = photos;
apiClient.albums = albums;
apiClient.faces = faces;
apiClient.search = search;
apiClient.settings = settings;
apiClient.setup = setup;
apiClient.management = management;
apiClient.agents = agents;
export default apiClient;
