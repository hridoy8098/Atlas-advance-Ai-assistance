// ArcReactor.jsx — animated arc-reactor core for the center stage.
import { T } from './theme'

const CSS = `
@keyframes jvSpin { to { transform: rotate(360deg); } }
@keyframes jvSpinRev { to { transform: rotate(-360deg); } }
@keyframes jvPulse { 0%,100% { opacity:.5; transform:scale(1); } 50% { opacity:.95; transform:scale(1.025); } }
@keyframes jvRipple { 0% { transform:scale(.82); opacity:.55; } 100% { transform:scale(1.35); opacity:0; } }
@keyframes jvTalk { 0%,100% { height:5px; opacity:.55; } 50% { height:20px; opacity:1; } }
@keyframes jvDot { 0%,100% { opacity:.25; transform:translateY(0); } 50% { opacity:1; transform:translateY(-3px); } }
@keyframes jvCoreGlow {
  0%,100% { box-shadow: 0 0 42px rgba(56,189,248,.30), inset 0 0 34px rgba(56,189,248,.14); }
  50% { box-shadow: 0 0 78px rgba(56,189,248,.52), inset 0 0 48px rgba(56,189,248,.24); }
}
@keyframes jvCoreBeat {
  0%,100% { transform: scale(1); opacity: .85; }
  50% { transform: scale(1.12); opacity: 1; }
}
@keyframes jvSweep { to { transform: rotate(360deg); } }
`

const ORBIT_DOTS = Array.from({ length: 10 })

export default function ArcReactor({ state = 'idle', size = 460, onClick }) {
  const listening = state === 'listening'
  const thinking = state === 'thinking'
  const speaking = state === 'speaking'
  const active = listening || thinking || speaking

  const spin = thinking ? '4s' : speaking ? '7s' : '24s'
  const reverse = thinking ? '2.8s' : '14s'
  const coreScale = listening ? 1.03 : 1

  const dots = ORBIT_DOTS.map((_, i) => {
    const angle = (i / ORBIT_DOTS.length) * Math.PI * 2 - Math.PI / 2
    return {
      left: `${50 + 41 * Math.cos(angle)}%`,
      top: `${50 + 41 * Math.sin(angle)}%`,
      bright: i % 2 === 0,
      delay: `${i * 0.15}s`,
    }
  })

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Toggle microphone"
      onClick={onClick}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick?.()
        }
      }}
      style={{
        position: 'relative',
        width: `clamp(280px, 42vh, ${size}px)`,
        height: `clamp(280px, 42vh, ${size}px)`,
        display: 'grid',
        placeItems: 'center',
        cursor: 'pointer',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      <style>{CSS}</style>

      {/* Ambient glow */}
      <div
        style={{
          position: 'absolute',
          inset: '2%',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(56,189,248,0.24) 0%, rgba(56,189,248,0.08) 40%, transparent 68%)',
          filter: 'blur(14px)',
          animation: 'jvPulse 4.5s ease-in-out infinite',
          pointerEvents: 'none',
        }}
      />

      {/* Outer ring */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          border: `1px solid rgba(56,189,248,${listening ? 0.65 : 0.34})`,
          animation: 'jvPulse 4.5s ease-in-out infinite',
          boxShadow: active ? '0 0 34px rgba(56,189,248,0.16)' : '0 0 46px rgba(56,189,248,0.07)',
        }}
      />

      {/* Tick ring */}
      <div
        style={{
          position: 'absolute',
          inset: '3%',
          borderRadius: '50%',
          background:
            'repeating-conic-gradient(from 0deg, rgba(56,189,248,0.6) 0deg 0.6deg, transparent 0.6deg 6deg)',
          WebkitMaskImage:
            'radial-gradient(circle, transparent 0 47.5%, #000 47.8% 49.2%, transparent 49.5%)',
          maskImage:
            'radial-gradient(circle, transparent 0 47.5%, #000 47.8% 49.2%, transparent 49.5%)',
          opacity: 0.7,
          animation: `jvSpin ${thinking ? 35 : 140}s linear infinite`,
        }}
      />

      {/* Rotating bright arc */}
      <div
        style={{
          position: 'absolute',
          inset: '6%',
          borderRadius: '50%',
          border: '2px solid transparent',
          borderTopColor: 'rgba(125,211,252,0.9)',
          borderRightColor: 'rgba(56,189,248,0.3)',
          filter: 'drop-shadow(0 0 6px rgba(56,189,248,0.45))',
          animation: `jvSpinRev ${reverse} linear infinite`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: '6%',
          borderRadius: '50%',
          border: '2px solid transparent',
          borderBottomColor: 'rgba(56,189,248,0.58)',
          borderLeftColor: 'rgba(56,189,248,0.14)',
          animation: `jvSpin ${thinking ? 2.2 : spin} linear infinite`,
        }}
      />

      {/* Dashed ring */}
      <div
        style={{
          position: 'absolute',
          inset: '12%',
          borderRadius: '50%',
          border: '1px dashed rgba(56,189,248,0.4)',
          animation: `jvSpinRev ${thinking ? 6 : 42}s linear infinite`,
        }}
      />

      {/* Orbiting dots */}
      <div style={{ position: 'absolute', inset: '8%', animation: `jvSpin ${thinking ? 5 : 26}s linear infinite` }}>
        {dots.map((dot, i) => (
          <span
            key={i}
            style={{
              position: 'absolute',
              left: dot.left,
              top: dot.top,
              width: 4,
              height: 4,
              marginLeft: -2,
              marginTop: -2,
              borderRadius: '50%',
              background: T.accent,
              boxShadow: `0 0 9px ${T.accent}`,
              opacity: dot.bright ? 0.95 : 0.4,
              animation: `jvDot ${listening ? 1.4 : 2.4}s ease-in-out ${dot.delay} infinite`,
            }}
          />
        ))}
      </div>

      {/* Inner rings */}
      <div style={{ position: 'absolute', inset: '19%', borderRadius: '50%', border: '1px solid rgba(56,189,248,0.26)' }} />
      <div style={{ position: 'absolute', inset: '24%', borderRadius: '50%', border: '1px solid rgba(56,189,248,0.15)' }} />

      {/* Conic sweep */}
      <div
        style={{
          position: 'absolute',
          inset: '19%',
          borderRadius: '50%',
          background:
            'conic-gradient(from 0deg, rgba(56,189,248,0) 0deg, rgba(56,189,248,0.26) 55deg, rgba(56,189,248,0) 110deg)',
          WebkitMaskImage: 'radial-gradient(circle, transparent 0 66%, #000 68% 100%)',
          maskImage: 'radial-gradient(circle, transparent 0 66%, #000 68% 100%)',
          animation: 'jvSweep 9s linear infinite',
          pointerEvents: 'none',
        }}
      />

      {/* Listening ripples */}
      {listening &&
        [0, 1].map(i => (
          <div
            key={i}
            style={{
              position: 'absolute',
              inset: '14%',
              borderRadius: '50%',
              border: '1px solid rgba(56,189,248,0.5)',
              animation: `jvRipple 2.1s ease-out ${i * 0.7}s infinite`,
              pointerEvents: 'none',
            }}
          />
        ))}

      {/* Core sphere */}
      <div
        style={{
          position: 'absolute',
          width: '42%',
          height: '42%',
          borderRadius: '50%',
          background: 'radial-gradient(circle at 50% 34%, #1b4f6e 0%, #0c2a44 46%, #04111d 100%)',
          border: '1px solid rgba(56,189,248,0.48)',
          animation: 'jvCoreGlow 3.6s ease-in-out infinite',
          transform: `scale(${coreScale})`,
          transition: 'transform 0.35s ease',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* 3D mesh */}
        <div
          style={{
            position: 'absolute',
            inset: '12% 4%',
            borderRadius: '50%',
            border: '1px solid rgba(56,189,248,0.12)',
            transform: 'rotate(-18deg)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: '0 21%',
            borderRadius: '50%',
            border: '1px solid rgba(56,189,248,0.10)',
            transform: 'rotate(14deg)',
          }}
        />

        {/* Hot center */}
        <div
          style={{
            position: 'absolute',
            width: '40%',
            height: '40%',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(224,247,255,0.95) 0%, rgba(125,211,252,0.55) 35%, rgba(56,189,248,0.12) 66%, transparent 100%)',
            filter: 'blur(1px)',
            animation: 'jvCoreBeat 3.2s ease-in-out infinite',
          }}
        />

        {/* Center activity */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 5 }}>
          {speaking
            ? [0, 1, 2, 3, 4].map(i => (
                <span
                  key={i}
                  style={{
                    width: 4,
                    height: 5,
                    borderRadius: 2,
                    background: '#e0f7ff',
                    boxShadow: '0 0 10px rgba(125,211,252,0.95)',
                    animation: `jvTalk 0.5s ease-in-out ${i * 0.08}s infinite`,
                  }}
                />
              ))
            : [0, 1, 2, 3, 4].map(i => (
                <span
                  key={i}
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: i === 2 ? '#ffffff' : '#bae6fd',
                    boxShadow: '0 0 12px rgba(125,211,252,0.95)',
                    animation: `jvDot ${thinking ? 1.1 : 2.2}s ease-in-out ${i * 0.16}s infinite`,
                  }}
                />
              ))}
        </div>
      </div>
    </div>
  )
}
