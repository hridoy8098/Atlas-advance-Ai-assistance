// src/services/api.js — Atlas 7.0 API Service
import axios from 'axios'

const SERVER_KEY = 'atlas_server_url'

export const isNativeApp = () =>
  Boolean(window.Capacitor?.isNativePlatform?.())

export const nativePlatform = () =>
  String(window.Capacitor?.getPlatform?.() || 'web').toLowerCase()

const cleanServer = (url) => String(url || '').trim().replace(/\/+$/, '')

// Optional build-time default so a hosted UI knows its backend without asking
// the visitor to paste a URL (set VITE_ATLAS_SERVER_URL when building).
const DEFAULT_SERVER = cleanServer(import.meta.env.VITE_ATLAS_SERVER_URL || '')

export const getServerUrl = () => {
  try {
    return cleanServer(localStorage.getItem(SERVER_KEY) || '') || DEFAULT_SERVER
  } catch {
    return DEFAULT_SERVER
  }
}

export const setServerUrl = (url) => {
  const value = cleanServer(url)
  try {
    if (value) localStorage.setItem(SERVER_KEY, value)
    else localStorage.removeItem(SERVER_KEY)
  } catch { /* storage unavailable */ }
  return value
}

export const getApiBase = () => {
  const server = getServerUrl()
  return server ? `${server}/api` : '/api'
}

export const checkServer = (url) => {
  const server = cleanServer(url)
  if (!server) return Promise.reject(new Error('Server URL is empty'))
  // Generous timeout: a sleeping free-tier instance can take ~50s to wake up.
  return axios.get(`${server}/api/health`, { timeout: 45000 }).then(r => r.data)
}

const api = axios.create({ baseURL: '/api', timeout: 15000 })

const TOKEN_KEY = 'atlas_session_token'

export const getAuthToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export const setAuthToken = (token) => {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* storage unavailable */ }
}

export const clearAuthToken = () => setAuthToken('')

// The phone can switch the laptop server without reloading the app.
api.interceptors.request.use(config => {
  config.baseURL = getApiBase()
  const token = getAuthToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// A 401 means the session expired or the PIN was never entered. The app
// listens for this event and shows the login screen again.
api.interceptors.response.use(
  response => response,
  error => {
    const url = String(error?.config?.url || '')
    if (error?.response?.status === 401 && !url.includes('/auth/pin')) {
      clearAuthToken()
      window.dispatchEvent(new Event('atlas:unauthorized'))
    }
    return Promise.reject(error)
  },
)

// ===== AUTH =====
export const verifyPin = (pin) => api.post('/auth/pin', { pin }).then(r => r.data)
export const lockSystem = () => api.post('/auth/logout').then(r => r.data)

// ===== COMMAND =====
// Agent commands can legitimately take 1-2 minutes on free AI tiers
// (Gemini quota fallback to Groq). Give them their own long timeout.
export const sendCommand = (command, platform) => api.post('/command', {
  command,
  platform: platform || (isNativeApp() ? nativePlatform() : 'desktop'),
  // The browser/WebView plays the Edge TTS reply, so don't double-play it on
  // the laptop speakers when the API is running locally.
  client_tts: true,
}, { timeout: 180000 }).then(r => r.data)

// ===== VOICE =====
export const getVoiceSpeaking = () => api.get('/voice/speaking').then(r => r.data)
export const stopSpeech = () => api.post('/voice/stop').then(r => r.data)
export const listenVoice = (duration = 5, language = 'auto', signal) => {
  const params = { duration }
  if (language && language !== 'auto') params.language = language
  return api
    .post('/voice/listen', null, {
      params,
      timeout: (duration + 20) * 1000,
      signal,
    })
    .then(r => r.data)
}
export const stopVoiceListen = () => api.post('/voice/listen/stop').then(r => r.data)

// Phone/WebView path: the client records and uploads the clip, the server
// transcribes it with Groq Whisper (the cloud box has no microphone).
export const transcribeAudio = (blob, language = 'auto') => {
  const type = (blob?.type || 'audio/webm').split(';')[0]
  const ext = type.includes('mp4') || type.includes('m4a') ? 'm4a'
    : type.includes('ogg') ? 'ogg'
    : type.includes('wav') ? 'wav'
    : type.includes('mpeg') ? 'mp3'
    : 'webm'

  const form = new FormData()
  form.append('file', blob, `voice.${ext}`)
  if (language && language !== 'auto') form.append('language', language)

  return api.post('/voice/transcribe', form, { timeout: 90000 }).then(r => r.data)
}

// Edge TTS on the server, returned as MP3 so the browser/phone can play it.
// Edge occasionally drops a connection on the free tier; retry once before
// falling back to the local browser voice.
export const fetchSpeech = async (text, language = 'auto') => {
  let lastError
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await api.post(
        '/voice/tts',
        { text, language },
        { responseType: 'blob', timeout: 30000 },
      )
    } catch (error) {
      lastError = error
      const status = error?.response?.status
      const retryable = !status || status === 408 || status === 429 || status >= 500
      if (!retryable || attempt === 1) throw error
      await new Promise(resolve => setTimeout(resolve, 400))
    }
  }
  throw lastError
}

// ===== SYSTEM =====
export const getMetrics = () => api.get('/system/metrics').then(r => r.data)
export const getWeather = () => api.get('/system/weather').then(r => r.data)
export const getPrayerTimes = () => api.get('/system/prayer-times').then(r => r.data)
export const getGroqStatus = () => api.get('/system/groq-status').then(r => r.data)

// ===== CONFIG =====
export const getUserConfig = () => api.get('/config').then(r => r.data)
export const getHealth = () => api.get('/health').then(r => r.data)

// ===== AGENTS =====
export const getAgents = () => api.get('/agents').then(r => r.data)
export const getAgentHealth = () => api.get('/agents/health').then(r => r.data)
export const toggleAgent = (id, enabled) => api.post(`/agents/${id}/toggle`, { enabled }).then(r => r.data)
export const bulkToggleAgents = (enabled, category) => api.post('/agents/bulk-toggle', { enabled, category }).then(r => r.data)
export const testAgent = (id) => api.post(`/agents/${id}/test`).then(r => r.data)
export const getAgent = (id) => api.get(`/agents/${id}`).then(r => r.data)

// ===== CONTACTS / CALLS =====
export const getContacts = () => api.get('/communication/contacts').then(r => r.data)
export const addContact = (name, phone, aliases = []) => api.post('/communication/contacts', { name, phone, aliases }).then(r => r.data)
export const deleteContact = (name) => api.delete(`/communication/contacts/${encodeURIComponent(name)}`).then(r => r.data)
export const whatsappCall = (contact, platform = 'desktop') => api.post('/communication/whatsapp/call', { contact, platform }).then(r => r.data)
export const getReceptionistStatus = () => api.get('/communication/receptionist/status').then(r => r.data)
export const setReceptionistBusy = (busy) => api.post('/communication/receptionist/busy', { busy }).then(r => r.data)
export const simulateReceptionistCall = (payload) => api.post('/communication/receptionist/simulate', payload).then(r => r.data)
export const getReceptionistCalls = (limit = 50) => api.get(`/communication/receptionist/calls?limit=${limit}`).then(r => r.data)
export const receptionistCallback = (callId, platform) => api.post(
  '/communication/receptionist/callback',
  { call_id: callId, platform: platform || (isNativeApp() ? nativePlatform() : 'desktop') },
).then(r => r.data)

// ===== LAPTOP CONNECTOR =====
export const getConnectorStatus = () => api.get('/connector/status').then(r => r.data)
export const getConnectorPairing = () => api.get('/connector/pairing').then(r => r.data)

export const optimizePC = () => api.post('/agent/optimize-pc').then(r => r.data)
export const cleanTemp = () => api.post('/agent/clean-temp').then(r => r.data)
export const listFiles = (path = '') => api.get('/agent/list-files?path=' + encodeURIComponent(path)).then(r => r.data)
export const searchFiles = (q) => api.get('/agent/search-files?query=' + encodeURIComponent(q)).then(r => r.data)
export const organizeDownloads = () => api.post('/agent/organize-downloads').then(r => r.data)
export const executeCommand = (cmd) => api.post('/agent/execute', { cmd }).then(r => r.data)

// ===== ANALYTICS =====
export const getAnalyticsOverview = (days = 7) => api.get(`/analytics/overview?days=${days}`).then(r => r.data)
export const getWeeklyReport = (days = 7) => api.get(`/analytics/weekly?days=${days}`).then(r => r.data)
export const logStudySession = (subject, minutes) => api.post('/analytics/study-session', { subject, minutes }).then(r => r.data)
export const addExpense = (amount, category, note) => api.post('/analytics/expense', { amount, category, note }).then(r => r.data)
export const getSpending = (days = 30) => api.get(`/analytics/spending?days=${days}`).then(r => r.data)
export const addHabit = (name) => api.post('/analytics/habit', { name }).then(r => r.data)
export const logHabit = (name) => api.post('/analytics/habit/log', { name }).then(r => r.data)
export const getHabits = () => api.get('/analytics/habits').then(r => r.data)

// ===== SECURITY =====
export const getSecurityOverview = () => api.get('/security/overview').then(r => r.data)
export const scanMalware = (maxFiles = 2000) => api.post('/security/scan', { max_files: maxFiles }, { timeout: 120000 }).then(r => r.data)
export const checkPassword = (password) => api.post('/security/password', { password }).then(r => r.data)
export const checkBreach = (email) => api.post('/security/breach', { email }, { timeout: 30000 }).then(r => r.data)
export const get2FAStatus = () => api.get('/security/2fa/status').then(r => r.data)
export const setPrivacyMode = (enable) => api.post('/security/privacy', { enable }).then(r => r.data)
export const setFakeScreen = (show) => api.post('/security/fake-screen', { show }).then(r => r.data)
export const watermarkScreen = (text = 'ATLAS') => api.post('/security/watermark', { text }, { timeout: 30000 }).then(r => r.data)
export const previewSelfDestruct = () => api.post('/security/self-destruct', { dry_run: true }).then(r => r.data)

// ===== STUDY =====
export const getFlashcards = (deck) => api.get('/study/flashcards' + (deck ? `?deck=${encodeURIComponent(deck)}` : '')).then(r => r.data)
export const addFlashcard = (question, answer, deck) => api.post('/study/flashcards', { question, answer, deck }).then(r => r.data)
export const deleteFlashcard = (id) => api.delete(`/study/flashcards/${id}`).then(r => r.data)
export const getDueCards = (limit = 20) => api.get(`/study/due?limit=${limit}`).then(r => r.data)
export const reviewCard = (cardId, quality) => api.post('/study/review', { card_id: cardId, quality }).then(r => r.data)
export const getStudyStats = () => api.get('/study/stats').then(r => r.data)
export const getConceptMap = (topic) => api.post('/study/concept-map', { topic }, { timeout: 60000 }).then(r => r.data)
export const getCitation = (fields, style = 'apa') => api.post('/study/citation', { fields, style }).then(r => r.data)
export const getStudyPlan = (subject, examDate, hoursPerDay) => api.post('/study/plan', { subject, exam_date: examDate, hours_per_day: hoursPerDay }).then(r => r.data)
export const explainTopic = (topic, level = 'medium') => api.post('/study/explain', { topic, level }, { timeout: 60000 }).then(r => r.data)

// ===== BANGLADESH =====
export const getBDNews = (limit = 10) => api.get(`/bd/news?limit=${limit}`, { timeout: 20000 }).then(r => r.data)
export const getBDCurrency = (base = 'BDT') => api.get(`/bd/currency?base=${base}`).then(r => r.data)
export const getBDStock = (limit = 10) => api.get(`/bd/stock?limit=${limit}`, { timeout: 20000 }).then(r => r.data)
export const getBDPrayer = (city = 'Dhaka') => api.get(`/bd/prayer?city=${encodeURIComponent(city)}`).then(r => r.data)

// ===== MEDIA =====
export const getMediaLibrary = () => api.get('/media/library').then(r => r.data)
export const getMediaStatus = () => api.get('/media/status').then(r => r.data)
export const playMedia = (path) => api.post('/media/play', { path }).then(r => r.data)
export const pauseMedia = () => api.post('/media/pause').then(r => r.data)
export const resumeMedia = () => api.post('/media/resume').then(r => r.data)
export const stopMedia = () => api.post('/media/stop').then(r => r.data)
export const generateMeme = (imagePath, top, bottom) => api.post('/media/meme', { image_path: imagePath, top, bottom }, { timeout: 30000 }).then(r => r.data)
export const removeBackground = (imagePath) => api.post('/media/remove-bg', { image_path: imagePath }, { timeout: 60000 }).then(r => r.data)
export const createPodcast = (script, voice) => api.post('/media/podcast', { script, voice }, { timeout: 120000 }).then(r => r.data)
export const generateSubtitles = (path) => api.post('/media/subtitle', { path }, { timeout: 120000 }).then(r => r.data)
export const downloadVideo = (url, audioOnly = false) => api.post('/media/download-video', { url, audio_only: audioOnly }, { timeout: 300000 }).then(r => r.data)
export const generateImage = (prompt, size = '1024x1024') => api.post('/media/generate-image', { prompt, size }, { timeout: 120000 }).then(r => r.data)

// ===== WEBSOCKET =====
export const createWebSocket = (onMessage) => {
  const server = getServerUrl()
  const token = getAuthToken()
  const query = token ? `?token=${encodeURIComponent(token)}` : ''
  let wsUrl
  if (server) {
    wsUrl = `${server.replace(/^http/, 'ws')}/ws${query}`
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    wsUrl = `${protocol}//${window.location.host}/ws${query}`
  }
  const ws = new WebSocket(wsUrl)
  ws.onopen = () => {
    console.log('🔌 Atlas WS connected')
    setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send('ping') }, 30000)
  }
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) } catch {}
  }
  ws.onerror = (e) => console.error('WS error:', e)
  return ws
}

export default api