// store/useAtlasStore.js — Zustand global state
import { create } from 'zustand'
import { getAuthToken, setAuthToken, clearAuthToken } from '../services/api'

const storedToken = getAuthToken()

const useAtlasStore = create((set, get) => ({
  // Auth
  isAuthenticated: Boolean(storedToken),
  sessionToken: storedToken || null,
  userName: 'Boss',

  // UI
  activePanel: 'chat',
  centerMode: 'reactor',
  voiceLang: 'auto',
  sessionStart: Date.now(),
  commandCount: 0,

  // Chat
  messages: [],
  isProcessing: false,

  // System metrics
  metrics: { cpu: 0, mem_used: 0, mem_percent: 0, disk_percent: 0, bat_percent: -1, bat_charging: false },

  // Weather
  weather: { temp: 30, desc: 'Partly Cloudy', humidity: 65, wind: 12, city: 'Dhaka' },

  // Prayer times
  prayerTimes: { fajr: '--:--', dhuhr: '--:--', asr: '--:--', maghrib: '--:--', isha: '--:--' },

  // Agents
  agents: [],
  agentsLoaded: false,
  agentsLoading: false,

  // WebSocket
  ws: null,

  // ===== ACTIONS =====
  setAuthenticated: (token) => {
    setAuthToken(token)
    set({ isAuthenticated: true, sessionToken: token })
  },
  logout: () => {
    clearAuthToken()
    set({ isAuthenticated: false, sessionToken: null, messages: [] })
  },
  setUserName: (name) => set({ userName: name }),
  setActivePanel: (panel) => set({ activePanel: panel }),
  setCenterMode: (mode) => set({ centerMode: mode }),
  setVoiceLang: (lang) => set({ voiceLang: lang }),
  incrementCommandCount: () => set(state => ({ commandCount: state.commandCount + 1 })),
  setMetrics: (metrics) => set({ metrics }),
  setWeather: (weather) => set({ weather }),
  setPrayerTimes: (prayerTimes) => set({ prayerTimes }),
  setAgents: (agents) => set({ agents, agentsLoaded: true, agentsLoading: false }),
  setAgentsLoading: (agentsLoading) => set({ agentsLoading }),
  updateAgent: (id, patch) => set(state => ({
    agents: state.agents.map(a => a.id === id ? { ...a, ...patch } : a),
  })),
  setWs: (ws) => set({ ws }),
  setProcessing: (v) => set({ isProcessing: v }),

  addMessage: (role, text) => set(state => ({
    messages: [...state.messages, {
      id: Date.now() + Math.random(),
      role,
      text,
      time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }]
  })),

  clearMessages: () => set({ messages: [] }),
}))

// Dev-only: browser console theke store access (window.__atlasStore.getState()...)
if (import.meta.env?.DEV) window.__atlasStore = useAtlasStore

export default useAtlasStore
