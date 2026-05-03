import { create } from "zustand";
import api from "../services/api";

const useAgentStore = create((set, get) => ({
  agents: [],
  loading: false,
  error: null,

  fetchAgents: async () => {
    set({ loading: true, error: null });
    try {
      const res = await api.agents.getStatus();
      set({ agents: res.data, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  runAgent: async (name) => {
    try {
      await api.agents.runAgent(name);
      await get().fetchAgents();
    } catch (err) {
      set({ error: err.message });
    }
  },

  toggleAgent: async (name, shouldStart) => {
    try {
      if (shouldStart) {
        await api.agents.startAgent(name);
      } else {
        await api.agents.stopAgent(name);
      }
      await get().fetchAgents();
    } catch (err) {
      set({ error: err.message });
    }
  },

  resetAgent: async (name) => {
    try {
      await api.agents.resetAgent(name);
      await get().fetchAgents();
    } catch (err) {
      set({ error: err.message });
    }
  },
}));

export default useAgentStore;
