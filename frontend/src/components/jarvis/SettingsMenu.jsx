// SettingsMenu.jsx — interface preferences popover.
import { useEffect, useRef } from 'react'
import { Bot, Languages, Monitor, RefreshCw, Sparkles, Wifi } from 'lucide-react'
import { getServerUrl, isNativeApp } from '../../services/api'
import { T } from './theme'

function Segmented({ value, options, onChange }) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 3,
        padding: 3,
        borderRadius: 9,
        background: 'rgba(3,9,16,0.75)',
        border: `1px solid ${T.border}`,
      }}
    >
      {options.map(opt => {
        const active = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            style={{
              flex: 1,
              padding: '7px 8px',
              borderRadius: 6,
              border: '1px solid',
              borderColor: active ? 'rgba(56,189,248,0.35)' : 'transparent',
              background: active ? 'rgba(56,189,248,0.13)' : 'transparent',
              color: active ? '#c9edff' : T.muted,
              fontSize: 11,
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.16s ease',
              whiteSpace: 'nowrap',
            }}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

export default function SettingsMenu({ open, onClose, centerMode, setCenterMode, voiceLang, setVoiceLang, onRefresh }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const handlePointer = e => {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    const handleKey = e => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handlePointer)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handlePointer)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      ref={ref}
      style={{
        position: 'absolute',
        top: 'calc(100% + 10px)',
        right: 0,
        width: 276,
        padding: 14,
        borderRadius: 12,
        background: 'linear-gradient(180deg, rgba(13,27,42,0.99) 0%, rgba(8,17,28,0.99) 100%)',
        border: `1px solid ${T.border}`,
        boxShadow: '0 24px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(56,189,248,0.04)',
        zIndex: 100,
        animation: 'jvPop 0.18s ease-out',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 13 }}>
        <Sparkles size={14} color={T.accent} />
        <span style={{ fontSize: 11.5, fontWeight: 600, color: T.text, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Interface Settings
        </span>
      </div>

      <div style={{ marginBottom: 13 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7, color: T.muted, fontSize: 11 }}>
          <Monitor size={13} />
          <span>Center display</span>
        </div>
        <Segmented
          value={centerMode}
          onChange={setCenterMode}
          options={[
            { value: 'reactor', label: 'Arc Reactor' },
            { value: 'robot', label: 'Atlas Robot' },
          ]}
        />
      </div>

      <div style={{ marginBottom: 13 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7, color: T.muted, fontSize: 11 }}>
          <Languages size={13} />
          <span>Voice language</span>
        </div>
        <Segmented
          value={voiceLang}
          onChange={setVoiceLang}
          options={[
            { value: 'auto', label: 'Auto' },
            { value: 'bn-BD', label: 'বাংলা' },
            { value: 'en-US', label: 'English' },
          ]}
        />
      </div>

      <div style={{ height: 1, background: T.borderSoft, margin: '12px 0' }} />

      <button
        type="button"
        className="jv-settings-item"
        onClick={() => {
          window.dispatchEvent(new Event('atlas:open-server-setup'))
          onClose()
        }}
        style={{ marginBottom: 4 }}
      >
        <Wifi size={14} />
        <span style={{ flex: 1, textAlign: 'left' }}>
          {isNativeApp() ? 'Laptop server' : 'Server connection'}
          <span style={{ display: 'block', fontSize: 9, color: T.dim, marginTop: 1 }}>
            {getServerUrl() || 'this device (local)'}
          </span>
        </span>
      </button>

      <button
        type="button"
        className="jv-settings-item"
        onClick={() => {
          onRefresh?.()
          onClose()
        }}
      >
        <RefreshCw size={14} />
        <span>Refresh dashboard data</span>
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 10, padding: '0 10px', color: T.dim, fontSize: 10 }}>
        <Bot size={11} />
        <span>Atlas v7.0 — local session</span>
      </div>
    </div>
  )
}
