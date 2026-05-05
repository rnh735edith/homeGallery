import { create } from 'zustand'
import { auth as authApi } from '../services/api'

export const useAuthStore = create((set, get) => ({
  user: null,
  token: localStorage.getItem('token') || null,
  isAuthenticated: !!localStorage.getItem('token'),
  loading: false,
  error: null,

  login: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const response = await authApi.login({ username, password })
      const token = response.data.access_token
      localStorage.setItem('token', token)
      set({ token, isAuthenticated: true, loading: false })
      await get().fetchUser()
      return true
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed'
      set({ error: message, loading: false })
      throw error
    }
  },

  register: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const response = await authApi.register({ username, password })
      const token = response.data.access_token
      localStorage.setItem('token', token)
      set({ token, isAuthenticated: true, loading: false })
      await get().fetchUser()
      return true
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration failed'
      set({ error: message, loading: false })
      throw error
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    set({ user: null, token: null, isAuthenticated: false, error: null })
  },

  fetchUser: async () => {
    const { token } = get()
    if (!token) return
    set({ loading: true })
    try {
      const response = await authApi.me()
      set({ user: response.data, loading: false })
    } catch (error) {
      set({ loading: false })
      get().logout()
    }
  },

  clearError: () => set({ error: null }),
}))
