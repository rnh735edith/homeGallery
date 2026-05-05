import { create } from 'zustand'
import api from '../services/api'

export const useDashboardStore = create((set) => ({
  metrics: null,
  logs: [],
  tasks: [],
  loading: false,
  error: null,

  fetchMetrics: async () => {
    set({ loading: true, error: null })
    try {
      const res = await api.get('/metrics/dashboard')
      set({ metrics: res.data })
    } catch (err) {
      set({ error: err.message })
    } finally {
      set({ loading: false })
    }
  },

  fetchLogs: async (limit = 100) => {
    try {
      const res = await api.get('/metrics/logs', { params: { limit } })
      set({ logs: res.data.logs || [] })
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    }
  },

  fetchQueue: async () => {
    try {
      const res = await api.get('/queue/')
      set({ tasks: res.data.tasks || [] })
    } catch (err) {
      console.error('Failed to fetch queue:', err)
    }
  },

  clearCompletedTasks: async () => {
    try {
      await api.post('/queue/clear-completed')
      set((state) => ({
        tasks: state.tasks.filter((t) => t.status === 'pending' || t.status === 'running'),
      }))
    } catch (err) {
      console.error('Failed to clear tasks:', err)
    }
  },
}))
