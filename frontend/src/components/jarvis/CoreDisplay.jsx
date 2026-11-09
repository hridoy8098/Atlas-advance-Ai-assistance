// CoreDisplay.jsx — reactor/robot stage, Atlas identity and status.
import AtlasRobot from '../hud/AtlasRobot'
import ArcReactor from './ArcReactor'
import ControlDock from './ControlDock'
import { T } from './theme'

function getStatus({ online, isListening, state }) {
  if (!online) return { text: 'System offline', color: T.red, dot: T.red }
  if (isListening) return { text: 'Listening...', color: '#bae6fd', dot: T.accent }
  if (state === 'thinking') return { text: 'Processing request...', color: '#fde68a', dot: T.amber }
  if (state === 'speaking') return { text: 'Speaking...', color: '#bae6fd', dot: T.accent }
  return { text: 'System online', color: '#bbf7d0', dot: T.green }
}

function Corner({ top, right, bottom, left }) {
  return (
    <span
      aria-hidden="true"
      style={{
        position: 'absolute',
        top,
        right,
        bottom,
        left,
        width: 22,
        height: 22,
        pointerEvents: 'none',
        borderTop: top ? '1px solid rgba(56,189,248,0.26)' : 'none',
        borderRight: right ? '1px solid rgba(56,189,248,0.26)' : 'none',
        borderBottom: bottom ? '1px solid rgba(56,189,248,0.26)' : 'none',
        borderLeft: left ? '1px solid rgba(56,189,248,0.26)' : 'none',
      }}
    />
  )
}

function TelemetryChip({ label, value, color = T.accent }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 7,
        padding: '5px 9px',
        borderRadius: 7,
        border: '1px solid rgba(56,189,248,0.10)',
        background: 'rgba(5,14,24,0.52)',
        backdropFilter: 'blur(6px)',
      }}
    >
      <span style={{ fontFamily: T.mono, fontSize: 8, letterSpacing: '0.16em', color: T.dim }}>{label}</span>
      <span style={{ fontFamily: T.mono, fontSize: 10, color, fontWeight: 500 }}>{value}</span>
    </div>
  )
}

export default function CoreDisplay({
  online,
  state,
  isListening,
  centerMode,
  onToggleMic,
  cameraOn,
  onToggleCamera,
  onFocusInput,
  metrics,
}) {
  const status = getStatus({ online, isListening, state })
  const idle = !isListening && state === 'idle' && online
  const cpu = Math.round(Number(metrics?.cpu) || 0)
  const mem = Math.round(Number(metrics?.mem_percent) || 0)
  const hasMetrics = Number.isFinite(Number(metrics?.cpu)) && Number.isFinite(Number(metrics?.mem_percent))

  return (
    <div
      style={{
        position: 'relative',
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 0 4px',
      }}
    >
      {/* HUD frame */}
      <Corner top={10} left={10} />
      <Corner top={10} right={10} />
      <Corner bottom={10} left={10} />
      <Corner bottom={10} right={10} />

      {/* Live telemetry */}
      <div
        style={{
          position: 'absolute',
          top: 14,
          left: 22,
          right: 22,
          display: 'flex',
          justifyContent: 'space-between',
          pointerEvents: 'none',
        }}
      >
        <TelemetryChip label="CORE LOAD" value={online && hasMetrics ? `${cpu}%` : '--'} color={hasMetrics && cpu >= 85 ? T.red : T.accent} />
        <TelemetryChip label="MEMORY" value={online && hasMetrics ? `${mem}%` : '--'} color={hasMetrics && mem >= 90 ? T.red : '#22d3ee'} />
      </div>

      {/* Side rails */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          left: 16,
          top: '50%',
          transform: 'translateY(-50%) rotate(180deg)',
          writingMode: 'vertical-rl',
          fontFamily: T.mono,
          fontSize: 8,
          letterSpacing: '0.3em',
          color: 'rgba(123,149,171,0.42)',
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
        }}
      >
        ATLAS · ARC REACTOR · MK VII
      </div>
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          right: 16,
          top: '50%',
          transform: 'translateY(-50%)',
          writingMode: 'vertical-rl',
          fontFamily: T.mono,
          fontSize: 8,
          letterSpacing: '0.3em',
          color: 'rgba(123,149,171,0.42)',
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
        }}
      >
        LOCAL NODE · SECTOR 01
      </div>

      {/* Stage */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        {/* Crosshair guides */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            left: '8%',
            right: '8%',
            top: '50%',
            height: 1,
            background: 'linear-gradient(90deg, transparent, rgba(56,189,248,0.16), transparent)',
            pointerEvents: 'none',
          }}
        />
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            top: '8%',
            bottom: '8%',
            left: '50%',
            width: 1,
            background: 'linear-gradient(180deg, transparent, rgba(56,189,248,0.12), transparent)',
            pointerEvents: 'none',
          }}
        />

        {centerMode === 'robot' ? (
          <div className="jv-robot-stage">
            <AtlasRobot
              state={isListening ? 'listening' : state}
              emotion={state === 'thinking' ? 'curious' : 'neutral'}
              onClick={onToggleMic}
            />
          </div>
        ) : (
          <ArcReactor state={isListening ? 'listening' : state} size={480} onClick={onToggleMic} />
        )}
      </div>

      {/* Identity */}
      <div style={{ textAlign: 'center', flexShrink: 0, marginTop: 2, position: 'relative' }}>
        <h1
          style={{
            margin: 0,
            fontFamily: T.display,
            fontSize: 'clamp(30px, 3.4vw, 44px)',
            fontWeight: 600,
            letterSpacing: '0.26em',
            paddingLeft: '0.26em',
            background: 'linear-gradient(180deg, #f4fcff 0%, #a5e2fb 52%, #38bdf8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            filter: 'drop-shadow(0 0 26px rgba(56,189,248,0.30))',
            lineHeight: 1.1,
          }}
        >
          ATLAS
        </h1>
        <div style={{ marginTop: 7, fontSize: 9.5, letterSpacing: '0.32em', color: T.dim, textTransform: 'uppercase' }}>
          Artificial Intelligence Core · v7.0
        </div>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 16,
            padding: '8px 16px',
            borderRadius: 999,
            background: 'rgba(6,16,26,0.72)',
            border: '1px solid rgba(56,189,248,0.16)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: status.dot,
              boxShadow: `0 0 9px ${status.dot}`,
              animation: idle ? 'jvDotPulse 2.2s ease-in-out infinite' : 'none',
            }}
          />
          <span style={{ fontSize: 11.5, color: status.color, fontWeight: 500 }}>{status.text}</span>
        </div>

        <div style={{ height: 15, marginTop: 4, fontSize: 10, color: T.dim }}>
          {idle ? 'Click the reactor or microphone to speak' : ''}
        </div>
      </div>

      <div style={{ marginTop: 8, paddingBottom: 2 }}>
        <ControlDock
          cameraOn={cameraOn}
          onToggleCamera={onToggleCamera}
          isListening={isListening}
          onToggleMic={onToggleMic}
          onFocusInput={onFocusInput}
        />
      </div>
    </div>
  )
}
