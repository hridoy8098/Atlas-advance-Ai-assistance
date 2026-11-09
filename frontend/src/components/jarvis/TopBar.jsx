// TopBar.jsx — Atlas identity, clock, weather and interface settings.
import { useEffect, useState } from 'react'
import { Bot, Clock, CloudSun, Settings } from 'lucide-react'
import SettingsMenu from './SettingsMenu'
import AgentPanel from './AgentPanel'
import useAtlasStore from '../../store/useAtlasStore'
import { getAgents } from '../../services/api'
import { T, pillStyle } from './theme'

export default function TopBar({ online, weather, centerMode, setCenterMode, voiceLang, setVoiceLang, onRefresh }) {
  const [time, setTime] = useState(new Date())
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [agentsOpen, setAgentsOpen] = useState(false)
  const { agents, agentsLoaded, setAgents } = useAtlasStore()

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (agentsLoaded) return
    let alive = true
    getAgents()
      .then(data => { if (alive) setAgents(data.agents || []) })
      .catch(() => {})
    return () => { alive = false }
  }, [agentsLoaded, setAgents])

  const enabledCount = agents.filter(a => a.enabled).length

  const clock = time.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true })
  const date = time.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
  const temp = Number(weather?.temp)
  const tempLabel = Number.isFinite(temp) ? `${temp.toFixed(1)}°C` : '--°C'

  return (
    <header
      className="jv-topbar"
      style={{
        height: 66,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        padding: '0 18px',
        position: 'relative',
        zIndex: 20,
        background: 'rgba(5,11,20,0.70)',
        backdropFilter: 'blur(18px)',
        borderBottom: `1px solid ${T.border}`,
      }}
    >
      {/* Brand */}
      <div className="jv-topbar-brand" style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <div
          style={{
            position: 'relative',
            width: 38,
            height: 38,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: '50%',
              border: '1px solid rgba(56,189,248,0.42)',
              boxShadow: '0 0 18px rgba(56,189,248,0.18), inset 0 0 12px rgba(56,189,248,0.08)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              inset: 4,
              borderRadius: '50%',
              border: '1px dashed rgba(56,189,248,0.28)',
              animation: 'jvSpin 16s linear infinite',
            }}
          />
          <span
            style={{
              fontFamily: T.display,
              fontSize: 15,
              fontWeight: 700,
              color: '#bae6fd',
              textShadow: '0 0 12px rgba(56,189,248,0.7)',
            }}
          >
            A
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontFamily: T.display,
                fontSize: 18,
                fontWeight: 600,
                letterSpacing: '0.24em',
                color: T.text,
                lineHeight: 1,
                whiteSpace: 'nowrap',
              }}
            >
              ATLAS
            </div>
            <div className="jv-topbar-subtitle" style={{ fontSize: 8.5, letterSpacing: '0.24em', color: T.dim, marginTop: 4 }}>A.I. CORE</div>
          </div>
          <div
            className="jv-topbar-online"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 9px',
              borderRadius: 999,
              border: `1px solid ${online ? 'rgba(34,197,94,0.28)' : 'rgba(239,68,68,0.3)'}`,
              background: online ? 'rgba(34,197,94,0.07)' : 'rgba(239,68,68,0.08)',
              whiteSpace: 'nowrap',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: online ? T.green : T.red,
                boxShadow: `0 0 7px ${online ? T.green : T.red}`,
                animation: online ? 'jvDotPulse 2.4s ease-in-out infinite' : 'none',
              }}
            />
            <span style={{ fontSize: 10.5, color: online ? '#86efac' : '#fca5a5', fontWeight: 500 }}>
              {online ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>
      </div>

      {/* Clock */}
      <div
        className="jv-topbar-clock"
        style={{
          ...pillStyle,
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '8px 14px',
          background: 'rgba(8,18,30,0.66)',
        }}
      >
        <Clock size={14} color={T.accent} strokeWidth={1.8} />
        <span style={{ fontFamily: T.mono, fontSize: 12, color: T.text, letterSpacing: '-0.01em' }}>{clock}</span>
        <span style={{ width: 1, height: 14, background: T.border, margin: '0 2px' }} />
        <span className="jv-topbar-date" style={{ fontSize: 11.5, color: T.muted }}>{date}</span>
      </div>

      {/* Weather + settings */}
      <div className="jv-topbar-right" style={{ display: 'flex', alignItems: 'center', gap: 9, flexShrink: 0 }}>
        <div className="jv-topbar-weather" style={{ ...pillStyle, gap: 8 }}>
          <CloudSun size={15} color={T.accent} strokeWidth={1.8} />
          <span style={{ fontFamily: T.mono, fontSize: 12, color: T.text }}>{tempLabel}</span>
          <span className="jv-topbar-weather-city" style={{ fontSize: 11, color: T.muted }}>{weather?.city || 'Dhaka'}</span>
        </div>

        <div style={{ position: 'relative' }}>
          <button
            type="button"
            className="jv-icon-btn"
            title="Agent control"
            aria-label="Agent control"
            onClick={() => setAgentsOpen(v => !v)}
            onMouseDown={e => e.stopPropagation()}
            style={{
              width: 38,
              height: 38,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 10,
              border: '1px solid',
              borderColor: agentsOpen ? 'rgba(56,189,248,0.38)' : T.border,
              background: agentsOpen ? T.accentSoft : 'rgba(8,18,30,0.6)',
              color: agentsOpen ? T.accent : T.muted,
              cursor: 'pointer',
              position: 'relative',
            }}
          >
            <Bot size={17} strokeWidth={1.7} />
            <span
              style={{
                position: 'absolute',
                top: -5,
                right: -5,
                minWidth: 16,
                height: 16,
                padding: '0 4px',
                borderRadius: 999,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: enabledCount ? 'rgba(34,197,94,0.18)' : 'rgba(56,189,248,0.12)',
                border: `1px solid ${enabledCount ? 'rgba(34,197,94,0.5)' : 'rgba(56,189,248,0.3)'}`,
                color: enabledCount ? '#86efac' : T.muted,
                fontFamily: T.mono,
                fontSize: 8.5,
                lineHeight: 1,
              }}
            >
              {agents.length ? enabledCount : '–'}
            </span>
          </button>
          <AgentPanel open={agentsOpen} onClose={() => setAgentsOpen(false)} />
        </div>

        <div style={{ position: 'relative' }}>
          <button
            type="button"
            className="jv-icon-btn"
            title="Interface settings"
            onClick={() => setSettingsOpen(v => !v)}
            onMouseDown={e => e.stopPropagation()}
            style={{
              width: 38,
              height: 38,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 10,
              border: '1px solid',
              borderColor: settingsOpen ? 'rgba(56,189,248,0.38)' : T.border,
              background: settingsOpen ? T.accentSoft : 'rgba(8,18,30,0.6)',
              color: settingsOpen ? T.accent : T.muted,
              cursor: 'pointer',
            }}
          >
            <Settings size={17} strokeWidth={1.7} />
          </button>
          <SettingsMenu
            open={settingsOpen}
            onClose={() => setSettingsOpen(false)}
            centerMode={centerMode}
            setCenterMode={setCenterMode}
            voiceLang={voiceLang}
            setVoiceLang={setVoiceLang}
            onRefresh={onRefresh}
          />
        </div>
      </div>
    </header>
  )
}
