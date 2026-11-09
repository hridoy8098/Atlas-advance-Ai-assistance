// ControlDock.jsx — camera, microphone and keyboard controls.
import { Keyboard, Mic, MicOff, Video, VideoOff } from 'lucide-react'
import { T } from './theme'

function DockButton({ title, active, onClick, children }) {
  return (
    <button
      type="button"
      className="jv-dock-btn"
      title={title}
      aria-label={title}
      onClick={onClick}
      style={{
        position: 'relative',
        width: 58,
        height: 58,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 14,
        border: '1px solid',
        borderColor: active ? 'rgba(56,189,248,0.45)' : T.border,
        background: active ? 'rgba(56,189,248,0.12)' : 'rgba(10,20,32,0.85)',
        color: active ? T.accent : T.muted,
        cursor: 'pointer',
        boxShadow: active ? '0 0 26px rgba(56,189,248,0.18), inset 0 1px 0 rgba(255,255,255,0.04)' : 'inset 0 1px 0 rgba(255,255,255,0.03)',
        flexShrink: 0,
      }}
    >
      {children}
      {active && (
        <span
          style={{
            position: 'absolute',
            bottom: 7,
            width: 4,
            height: 4,
            borderRadius: '50%',
            background: T.accent,
            boxShadow: `0 0 8px ${T.accent}`,
          }}
        />
      )}
    </button>
  )
}

export default function ControlDock({ cameraOn, onToggleCamera, isListening, onToggleMic, onFocusInput }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flexShrink: 0 }}>
      <DockButton title={cameraOn ? 'Turn camera off' : 'Turn camera on'} active={cameraOn} onClick={onToggleCamera}>
        {cameraOn ? <Video size={22} strokeWidth={1.7} /> : <VideoOff size={22} strokeWidth={1.7} />}
      </DockButton>

      <DockButton title={isListening ? 'Stop listening' : 'Talk to Atlas'} active={isListening} onClick={onToggleMic}>
        {isListening ? <MicOff size={22} strokeWidth={1.7} /> : <Mic size={22} strokeWidth={1.7} />}
        {isListening && (
          <span
            style={{
              position: 'absolute',
              inset: -1,
              borderRadius: 14,
              border: '1px solid rgba(56,189,248,0.55)',
              animation: 'jvPulse 1.6s ease-in-out infinite',
              pointerEvents: 'none',
            }}
          />
        )}
      </DockButton>

      <DockButton title="Focus message input" onClick={onFocusInput}>
        <Keyboard size={22} strokeWidth={1.7} />
      </DockButton>
    </div>
  )
}
