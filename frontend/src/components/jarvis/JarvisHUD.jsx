// JarvisHUD.jsx — main JARVIS-style Atlas dashboard.
import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import useAtlasStore from '../../store/useAtlasStore'
import { getHealth, getMetrics, getUserConfig, getWeather, stopSpeech } from '../../services/api'
import useAtlasChat from '../../hooks/useAtlasChat'
import useMicrophone from '../../hooks/useMicrophone'
import { stopPlayback } from '../../services/voice'
import TopBar from './TopBar'
import SystemStatsCard from './SystemStatsCard'
import WeatherCard from './WeatherCard'
import CameraCard from './CameraCard'
import UptimeCard from './UptimeCard'
import CoreDisplay from './CoreDisplay'
import ConversationPanel from './ConversationPanel'

export default function JarvisHUD() {
  const {
    metrics,
    weather,
    userName,
    centerMode,
    voiceLang,
    sessionStart,
    commandCount,
    setMetrics,
    setWeather,
    setUserName,
    setCenterMode,
    setVoiceLang,
  } = useAtlasStore()

  const [online, setOnline] = useState(true)
  const [cameraOn, setCameraOn] = useState(false)
  const [chatState, setChatState] = useState('idle')
  const inputRef = useRef(null)

  const loadMetrics = useCallback(async () => {
    try {
      const data = await getMetrics()
      if (data) setMetrics(data)
    } catch {}
  }, [setMetrics])

  const loadWeather = useCallback(async () => {
    try {
      const data = await getWeather()
      if (data) setWeather(data)
    } catch {}
  }, [setWeather])

  useEffect(() => {
    loadMetrics()
    const id = setInterval(loadMetrics, 3000)
    return () => clearInterval(id)
  }, [loadMetrics])

  useEffect(() => {
    loadWeather()
    const id = setInterval(loadWeather, 10 * 60 * 1000)
    return () => clearInterval(id)
  }, [loadWeather])

  useEffect(() => {
    getUserConfig()
      .then(cfg => {
        if (cfg?.user_name) setUserName(cfg.user_name)
      })
      .catch(() => {})
  }, [setUserName])

  useEffect(() => {
    let alive = true
    const check = async () => {
      try {
        const health = await getHealth()
        if (alive) setOnline(health?.status === 'ok')
      } catch {
        if (alive) setOnline(false)
      }
    }
    check()
    const id = setInterval(check, 15000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  // Chat
  const chat = useAtlasChat({ onStateChange: setChatState })
  const { send: sendChat, messages, isProcessing } = chat

  // Voice input: record on the phone, transcribe on the server.
  const mic = useMicrophone({
    language: voiceLang,
    onText: text => sendChat(text),
    onError: message => toast.error(message),
  })

  const toggleMic = useCallback(() => {
    if (mic.listening) {
      mic.stop()
      return
    }
    if (chatState === 'speaking') {
      stopSpeech().catch(() => {})
      stopPlayback()
    }
    mic.start()
  }, [chatState, mic])

  const refreshAll = useCallback(async () => {
    const results = await Promise.allSettled([loadMetrics(), loadWeather()])
    if (results.some(r => r.status === 'fulfilled')) toast.success('Dashboard refreshed')
    else toast.error('Refresh failed')
  }, [loadMetrics, loadWeather])

  return (
    <div className="jarvis-shell">
      <TopBar
        online={online}
        weather={weather}
        centerMode={centerMode}
        setCenterMode={setCenterMode}
        voiceLang={voiceLang}
        setVoiceLang={setVoiceLang}
        onRefresh={refreshAll}
      />

      <div className="jarvis-grid">
        <aside className="jarvis-left">
          <SystemStatsCard metrics={metrics} onRefresh={loadMetrics} />
          <WeatherCard weather={weather} onRefresh={loadWeather} />
          <CameraCard active={cameraOn} onToggle={() => setCameraOn(v => !v)} />
          <UptimeCard metrics={metrics} sessionStart={sessionStart} commandCount={commandCount} />
        </aside>

        <main className="jarvis-center">
          <CoreDisplay
            online={online}
            state={chatState}
            isListening={mic.listening}
            centerMode={centerMode}
            onToggleMic={toggleMic}
            cameraOn={cameraOn}
            onToggleCamera={() => setCameraOn(v => !v)}
            onFocusInput={() => inputRef.current?.focus()}
            metrics={metrics}
          />
        </main>

        <aside className="jarvis-right">
          <ConversationPanel
            messages={messages}
            isProcessing={isProcessing}
            onSend={sendChat}
            onClear={chat.clear}
            inputRef={inputRef}
            isListening={mic.listening}
            userName={userName}
          />
        </aside>
      </div>
    </div>
  )
}
