import { create } from "zustand";
import api from "../services/api";

export const useGalleryStore = create((set, get) => ({
  photos: [],
  albums: [],
  loading: false,
  currentPage: 1,
  totalPages: 1,
  totalPhotos: 0,
  filters: {},
  photoMetadatas: {},
  loadingMetadata: false,
  analysisData: {},
  enhancedPhotos: new Set(),

  fetchPhotos: async (params = {}) => {
    set({ loading: true });
    try {
      const res = await api.photos.list(params);
      set({
        photos: res.data.photos || res.data || [],
        currentPage: res.data.page || 1,
        totalPages: res.data.total_pages || 1,
        totalPhotos: res.data.total || 0,
        filters: params,
      });
    } catch (err) {
      console.error("Failed to fetch photos:", err);
    } finally {
      set({ loading: false });
    }
  },

  fetchAlbums: async () => {
    try {
      const res = await api.albums.list();
      console.log("fetchAlbums raw response:", res.data);
      const albumsData = Array.isArray(res.data)
        ? res.data
        : res.data.albums || [];
      console.log("fetchAlbums processed:", albumsData);
      set({ albums: albumsData });
    } catch (err) {
      console.error("Failed to fetch albums:", err);
    }
  },

  toggleFavorite: async (id) => {
    try {
      await api.photos.toggleFavorite(id);
      set((state) => ({
        photos: state.photos.map((p) =>
          p.id === id ? { ...p, favorite: !p.favorite } : p,
        ),
      }));
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
    }
  },

  deletePhoto: async (id) => {
    try {
      await api.photos.delete(id);
      set((state) => ({
        photos: state.photos.filter((p) => p.id !== id),
      }));
    } catch (err) {
      console.error("Failed to delete photo:", err);
    }
  },

  uploadPhoto: async (file, onProgress) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await api.photos.upload(formData, onProgress);
      set((state) => ({
        photos: [res.data, ...state.photos],
      }));
      return res.data;
    } catch (err) {
      console.error("Failed to upload photo:", err);
      throw err;
    }
  },

  fetchPhotoMetadata: async (photoId) => {
    const cached = get().photoMetadatas[photoId];
    if (cached) return cached;

    set((state) => ({ loadingMetadata: true }));
    try {
      const response = await api.metadata.get(photoId);
      set((state) => ({
        photoMetadatas: { ...state.photoMetadatas, [photoId]: response.data },
        loadingMetadata: false,
      }));
      return response.data;
    } catch (err) {
      set((state) => ({
        photoMetadatas: { ...state.photoMetadatas, [photoId]: null },
        loadingMetadata: false,
      }));
      console.error(`Failed to fetch metadata for photo ${photoId}:`, err);
      return null;
    }
  },

  fetchMetadataForPhotos: async (photoIds) => {
    const { photoMetadatas } = get();
    const idsToFetch = photoIds.filter((id) => !photoMetadatas[id]);

    if (idsToFetch.length === 0) return;

    set({ loadingMetadata: true });
    const updates = {};
    const promises = idsToFetch.map(async (id) => {
      try {
        const response = await api.metadata.get(id);
        updates[id] = response.data;
      } catch {
        updates[id] = null;
      }
    });
    await Promise.all(promises);
    set((state) => ({
      photoMetadatas: { ...state.photoMetadatas, ...updates },
      loadingMetadata: false,
    }));
  },

  clearPhotoMetadata: () => {
    set({ photoMetadatas: {}, loadingMetadata: false });
  },

  fetchAnalysis: async (photoId) => {
    const { analysisData } = get();
    if (analysisData[photoId]) return analysisData[photoId];

    try {
      const response = await api.analysis.getAnalysis(photoId);
      set((state) => ({
        analysisData: { ...state.analysisData, [photoId]: response.data },
      }));
      return response.data;
    } catch (err) {
      console.error(`Failed to fetch analysis for photo ${photoId}:`, err);
      return null;
    }
  },

  markAsEnhanced: (photoId) => {
    set((state) => ({
      enhancedPhotos: new Set([...state.enhancedPhotos, photoId]),
    }));
  },

  isEnhanced: (photoId) => {
    return get().enhancedPhotos.has(photoId);
  },
}));
