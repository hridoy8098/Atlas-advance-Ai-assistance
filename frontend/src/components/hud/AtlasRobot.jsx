// AtlasRobot.jsx — JARVIS-style expressive robot
// Face expressions + emotions + eye tracking + state animations
import { useEffect, useRef, useState } from 'react'

// ── Palettes ────────────────────────────────────────────────
const STATE_COLORS = {
  idle:      { main: '#38bdf8', glow: 'rgba(56,189,248,0.35)' },
  listening: { main: '#22d3ee', glow: 'rgba(34,211,238,0.5)' },
  thinking:  { main: '#818cf8', glow: 'rgba(129,140,248,0.5)' },
  speaking:  { main: '#0ea5e9', glow: 'rgba(14,165,233,0.5)' },
}

const EMOTION_COLORS = {
  happy: '#34d399',
  error: '#ef4444',
  alert: '#f59e0b',
}

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@400;500;600&family=Share+Tech+Mono&display=swap');

@keyframes roFloat    { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-7px)} }
@keyframes roBob      { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-3px)} }
@keyframes roRing     { 0%{transform:translate(-50%,-50%) scale(1);opacity:0.55} 100%{transform:translate(-50%,-50%) scale(2.4);opacity:0} }
@keyframes roSpin     { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
@keyframes roSpinSlow { from{transform:rotate(0deg)} to{transform:rotate(-360deg)} }
@keyframes roAntenna  { 0%,100%{box-shadow:0 0 6px currentColor,0 0 12px currentColor} 50%{box-shadow:0 0 15px currentColor,0 0 28px currentColor} }
@keyframes roTalk     { 0%,100%{height:4px} 50%{height:15px} }
@keyframes roDot      { 0%,100%{transform:translateY(0);opacity:0.35} 50%{transform:translateY(-5px);opacity:1} }
@keyframes roMarker   { 0%,100%{transform:translateY(0);opacity:0.95} 50%{transform:translateY(-4px);opacity:0.45} }
@keyframes roShake    { 0%,100%{transform:rotate(0deg)} 25%{transform:rotate(-2.4deg)} 75%{transform:rotate(2.4deg)} }
@keyframes roBootEye  { 0%{transform:scaleY(0)} 14%{transform:scaleY(1)} 26%{transform:scaleY(0.1)} 40%{transform:scaleY(1)} 54%{transform:scaleY(0.35)} 70%{transform:scaleY(1)} 100%{transform:scaleY(1)} }
@keyframes roSweep    { from{left:-14%;opacity:0.95} to{left:106%;opacity:0} }
@keyframes roScan     { 0%{top:12%} 100%{top:88%} }
@keyframes roReactor  { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
`

function StyleOnce() {
  if (typeof document !== 'undefined' && !document.getElementById('atlas-robot-style')) {
    const s = document.createElement('style')
    s.id = 'atlas-robot-style'
    s.textContent = CSS
    document.head.appendChild(s)
  }
  return null
}

// ── Eye ─────────────────────────────────────────────────────
function Eye({ side, emotion, blink, boot, gaze, color, state }) {
  const isArc = emotion === 'happy' || (emotion === 'wink' && side === 'right')
  const isSquint = emotion === 'error'
  const isAlert = emotion === 'alert'
  const isFocused = emotion === 'focused'

  const wrap = {
    position: 'relative',
    width: 26,
    height: 26,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'transform 90ms ease-out',
    transform: blink
      ? 'scaleY(0.08)'
      : isSquint
        ? 'scaleY(0.5)'
        : isFocused
          ? 'scaleY(0.78)'
          : 'scaleY(1)',
    animation: boot ? 'roBootEye 1.05s ease-out 1' : 'none',
  }

  if (isArc) {
    return (
      <div style={wrap}>
        <div style={{
          width: 22, height: 11,
          borderTop: `3px solid ${color}`,
          borderRadius: '50% 50% 0 0',
          filter: `drop-shadow(0 0 5px ${color})`,
          transition: 'transform 90ms',
          transform: blink ? 'scaleY(0.1)' : 'scaleY(1)',
        }} />
      </div>
    )
  }

  const lensSize = isAlert ? { w: 26, h: 27 } : { w: 22, h: 24 }
  const pupil = isAlert ? 6 : isSquint ? 8 : 10

  return (
    <div style={wrap}>
      <div style={{
        width: lensSize.w, height: lensSize.h,
        borderRadius: '50%',
        background: 'radial-gradient(circle at 50% 38%, rgba(56,189,248,0.16), rgba(0,0,0,0.6) 72%)',
        border: `1.5px solid ${color}aa`,
        boxShadow: `0 0 10px ${color}44, inset 0 0 8px ${color}22`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all 220ms ease',
      }}>
        <div style={{
          width: pupil, height: pupil,
          borderRadius: '50%',
          background: color,
          boxShadow: `0 0 9px ${color}`,
          position: 'relative',
          transform: `translate(${gaze.x}px, ${gaze.y}px)`,
          transition: 'transform 110ms ease-out, width 200ms, height 200ms',
        }}>
          <div style={{
            position: 'absolute', top: 1.5, left: 2,
            width: 2.5, height: 2.5, borderRadius: '50%',
            background: '#ffffff', opacity: 0.9,
          }} />
        </div>
      </div>
    </div>
  )
}

// ── Eyebrow ─────────────────────────────────────────────────
function Brow({ side, emotion, color }) {
  const style = {
    width: 20, height: 3,
    borderRadius: 2,
    background: color,
    opacity: 0.75,
    boxShadow: `0 0 6px ${color}66`,
    transition: 'all 260ms ease',
  }
  if (emotion === 'happy' || emotion === 'wink') style.opacity = 0
  else if (emotion === 'curious' && side === 'left') {
    style.transform = 'rotate(-16deg) translateY(-2px)'
    style.opacity = 0.95
  } else if (emotion === 'alert') {
    style.transform = 'translateY(-3px)'
    style.height = 3.5
    style.opacity = 1
  } else if (emotion === 'focused') {
    style.transform = `rotate(${side === 'left' ? 13 : -13}deg) translateY(2px)`
  } else if (emotion === 'error') {
    style.transform = `rotate(${side === 'left' ? 24 : -24}deg) translateY(2px)`
    style.background = '#ef4444'
  }
  return <div style={style} />
}

// ── Mouth ───────────────────────────────────────────────────
function Mouth({ state, emotion, color }) {
  if (state === 'speaking') {
    return (
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2.5, height: 18, justifyContent: 'center' }}>
        {[0, 0.09, 0.18, 0.09, 0].map((d, i) => (
          <div key={i} style={{
            width: 3, borderRadius: 2, background: color,
            animation: `roTalk 0.42s ease-in-out ${d}s infinite`,
            boxShadow: `0 0 5px ${color}`,
          }} />
        ))}
      </div>
    )
  }

  const line = (extra = {}) => (
    <div style={{
      width: 20, height: 2.5, borderRadius: 2,
      background: color, opacity: 0.65,
      boxShadow: `0 0 5px ${color}55`,
      transition: 'all 260ms ease',
      ...extra,
    }} />
  )

  if (emotion === 'happy') return (
    <div style={{
      width: 24, height: 11,
      borderBottom: `3px solid ${color}`,
      borderRadius: '0 0 60px 60px',
      marginTop: -2,
      filter: `drop-shadow(0 0 4px ${color})`,
    }} />
  )
  if (emotion === 'error') return line({ width: 16, opacity: 0.55, background: '#ef4444', boxShadow: '0 0 5px #ef4444' })
  if (emotion === 'curious') return (
    <div style={{ width: 7, height: 7, borderRadius: '50%', border: `2px solid ${color}`, marginTop: -2, boxShadow: `0 0 5px ${color}66` }} />
  )
  if (emotion === 'alert') return (
    <div style={{ width: 10, height: 8, borderRadius: '40%', border: `2px solid ${color}`, marginTop: -1, boxShadow: `0 0 5px ${color}66` }} />
  )
  if (emotion === 'focused') return line({ width: 14, opacity: 0.85 })
  return line()
}

// ── Main Robot ──────────────────────────────────────────────
export default function AtlasRobot({ state = 'idle', emotion = 'neutral', onClick }) {
  const [blink, setBlink] = useState(false)
  const [boot, setBoot] = useState(true)
  const [gaze, setGaze] = useState({ x: 0, y: 0 })
  const [previewEmotion, setPreviewEmotion] = useState(null)
  const [previewState, setPreviewState] = useState(null)

  const wrapRef = useRef(null)
  const lastMouseMove = useRef(Date.now())

  const effEmotion = previewEmotion ?? emotion
  const effState = previewState ?? state

  const c = STATE_COLORS[effState] || STATE_COLORS.idle
  const color = EMOTION_COLORS[effEmotion] || c.main

  // ── Boot sequence (eyes power on) ──
  useEffect(() => {
    const t = setTimeout(() => setBoot(false), 1400)
    return () => clearTimeout(t)
  }, [])

  // ── Random blink (occasional double-blink) ──
  useEffect(() => {
    let t1, t2, t3, t4
    const schedule = () => {
      t1 = setTimeout(() => {
        setBlink(true)
        t2 = setTimeout(() => {
          setBlink(false)
          if (Math.random() < 0.22) {
            t3 = setTimeout(() => setBlink(true), 150)
            t4 = setTimeout(() => { setBlink(false); schedule() }, 330)
          } else schedule()
        }, 110)
      }, 2200 + Math.random() * 3800)
    }
    schedule()
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4) }
  }, [])

  // ── Eye tracking (mouse follow) + idle wander ──
  useEffect(() => {
    const clamp = (v, m) => Math.max(-m, Math.min(m, v))
    const onMove = (e) => {
      lastMouseMove.current = Date.now()
      const el = wrapRef.current
      if (!el) return
      const r = el.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const cy = r.top + r.height * 0.32
      const nx = clamp((e.clientX - cx) / 55, 3.5)
      const ny = clamp((e.clientY - cy) / 70, 2.5)
      setGaze(prev => (Math.abs(prev.x - nx) > 0.4 || Math.abs(prev.y - ny) > 0.4) ? { x: nx, y: ny } : prev)
    }
    window.addEventListener('mousemove', onMove)

    const wander = setInterval(() => {
      if (Date.now() - lastMouseMove.current < 4000) return
      setGaze({ x: (Math.random() - 0.5) * 6, y: (Math.random() - 0.5) * 3.5 })
      setTimeout(() => setGaze({ x: 0, y: 0 }), 1500)
    }, 6500)

    return () => { window.removeEventListener('mousemove', onMove); clearInterval(wander) }
  }, [])

  // ── Dev preview hooks (window.__atlasEmote('happy', 'speaking')) ──
  useEffect(() => {
    if (!import.meta.env?.DEV) return
    window.__atlasEmote = (e, s) => { if (e !== undefined) setPreviewEmotion(e); if (s !== undefined) setPreviewState(s) }
    return () => { delete window.__atlasEmote }
  }, [])

  // ── Effective gaze (state/emotion overrides mouse follow) ──
  let g = gaze
  if (boot) g = { x: 0, y: 0 }
  else if (effState === 'thinking') g = { x: -2.6, y: -2.2 }
  else if (effEmotion === 'curious') g = { x: 1.8, y: -2.2 }
  else if (effEmotion === 'error') g = { x: 0, y: 1.8 }
  else if (effState === 'listening') g = { x: gaze.x * 0.4, y: -1 }

  const tilt =
    effState === 'listening' ? 'rotate(5deg)' :
    effState === 'thinking' ? 'rotate(-5deg)' :
    effState === 'speaking' ? 'rotate(1.5deg)' :
    effEmotion === 'curious' ? 'rotate(-3deg)' : 'rotate(0deg)'

  const LABELS = {
    idle: '● STANDBY',
    listening: '◉ LISTENING...',
    thinking: '◌ THINKING...',
    speaking: '▶ SPEAKING...',
  }

  return (
    <div
      onClick={onClick}
      title="Click to speak"
      style={{
        position: 'relative',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        width: 168, flexShrink: 0,
        userSelect: 'none', cursor: 'pointer',
      }}
    >
      <StyleOnce />

      {/* Body float (wrapped so gaze rect is stable) */}
      <div ref={wrapRef} style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {/* Listening pulse rings */}
        {effState === 'listening' && [0, 1, 2].map(i => (
          <div key={i} style={{
            position: 'absolute', width: 150, height: 150, borderRadius: '50%',
            border: `1.5px solid ${c.main}`, opacity: 0.5,
            animation: `roRing 2s ease-out ${i * 0.66}s infinite`,
            top: '42%', left: '50%',
            transform: 'translate(-50%,-50%)',
            pointerEvents: 'none',
          }} />
        ))}

        {/* Thinking orbit ring */}
        {effState === 'thinking' && (
          <div style={{ position: 'absolute', top: '30%', left: '50%', transform: 'translate(-50%,-50%)', width: 118, height: 118, pointerEvents: 'none' }}>
            <div style={{ width: '100%', height: '100%', borderRadius: '50%', border: `1.5px dashed ${c.main}55`, animation: 'roSpin 6s linear infinite' }} />
          </div>
        )}

        {/* Thinking thought-dots */}
        {effState === 'thinking' && (
          <div style={{ position: 'absolute', top: -4, right: 14, display: 'flex', gap: 3, pointerEvents: 'none' }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 5, height: 5, borderRadius: '50%', background: c.main,
                animation: `roDot 1s ease-in-out ${i * 0.18}s infinite`,
                boxShadow: `0 0 6px ${c.main}`,
              }} />
            ))}
          </div>
        )}

        {/* Emotion marker (? / !) */}
        {(effEmotion === 'curious' || effEmotion === 'alert') && (
          <div style={{
            position: 'absolute', top: -8, right: 10,
            fontFamily: 'Orbitron, monospace', fontSize: 16, fontWeight: 700,
            color: effEmotion === 'alert' ? '#f59e0b' : color,
            textShadow: '0 0 8px currentColor',
            animation: 'roMarker 1.6s ease-in-out infinite',
            pointerEvents: 'none',
          }}>
            {effEmotion === 'curious' ? '?' : '!'}
          </div>
        )}

        {/* Robot assembly */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          filter: `drop-shadow(0 0 18px ${c.glow})`,
          animation: effState === 'idle' && !boot ? 'roFloat 4.2s ease-in-out infinite' : 'none',
          position: 'relative',
        }}>

          {/* Antenna */}
          <div style={{ width: 2, height: 16, background: `${c.main}44`, margin: '0 auto' }} />
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: color,
            color: color,
            margin: '-4px auto 0',
            animation: 'roAntenna 1.6s ease-in-out infinite',
          }} />

          {/* Head (tilt + bob + error shake) */}
          <div style={{ marginTop: 4, transform: tilt, transition: 'transform 400ms ease' }}>
            <div style={{
              animation:
                effEmotion === 'error' ? 'roShake 0.45s ease-in-out 2' :
                effState === 'speaking' ? 'roBob 0.6s ease-in-out infinite' : 'none',
            }}>
              <div style={{
                width: 104, height: 76,
                background: 'linear-gradient(150deg, #071827, #0b2237)',
                border: `1.5px solid ${c.main}55`,
                borderRadius: 16,
                position: 'relative',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: `inset 0 0 14px rgba(0,0,0,0.5)`,
              }}>
                {/* Ears */}
                {[-1, 1].map(s => (
                  <div key={s} style={{
                    position: 'absolute', top: '50%', transform: 'translateY(-50%)',
                    [s === -1 ? 'left' : 'right']: -6,
                    width: 5, height: 24, borderRadius: 3,
                    background: `${c.main}33`,
                    border: `1px solid ${c.main}44`,
                  }} />
                ))}

                {/* Face screen */}
                <div style={{
                  position: 'absolute', inset: 7,
                  borderRadius: 11,
                  background: 'radial-gradient(circle at 50% 28%, rgba(8,32,52,0.95), rgba(3,8,14,0.98))',
                  border: `1px solid ${c.main}30`,
                  overflow: 'hidden',
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center',
                  gap: 3,
                }}>
                  {/* Subtle screen scan line */}
                  <div style={{
                    position: 'absolute', left: 0, right: 0, height: 1,
                    background: `${c.main}30`,
                    animation: 'roScan 3.6s linear infinite',
                    pointerEvents: 'none',
                  }} />

                  {/* Boot sweep */}
                  {boot && (
                    <div style={{
                      position: 'absolute', top: 0, bottom: 0, width: 3,
                      background: `linear-gradient(180deg, transparent, ${c.main}, transparent)`,
                      boxShadow: `0 0 12px ${c.main}`,
                      animation: 'roSweep 1.1s ease-out 1',
                      pointerEvents: 'none',
                    }} />
                  )}

                  {/* Brows */}
                  <div style={{ display: 'flex', gap: 26, marginBottom: 1 }}>
                    <Brow side="left" emotion={effEmotion} color={color} />
                    <Brow side="right" emotion={effEmotion} color={color} />
                  </div>

                  {/* Eyes */}
                  <div style={{ display: 'flex', gap: 22 }}>
                    <Eye side="left" emotion={effEmotion} blink={blink} boot={boot} gaze={g} color={color} state={effState} />
                    <Eye side="right" emotion={effEmotion} blink={blink} boot={boot} gaze={g} color={color} state={effState} />
                  </div>

                  {/* Mouth */}
                  <div style={{ marginTop: 2 }}>
                    <Mouth state={effState} emotion={effEmotion} color={color} />
                  </div>

                  {/* Happy cheeks */}
                  {effEmotion === 'happy' && [-1, 1].map(s => (
                    <div key={s} style={{
                      position: 'absolute', bottom: 9,
                      [s === -1 ? 'left' : 'right']: 9,
                      width: 8, height: 8, borderRadius: '50%',
                      background: color, opacity: 0.45,
                      filter: 'blur(1px)',
                      boxShadow: `0 0 9px ${color}`,
                    }} />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Neck */}
          <div style={{ width: 14, height: 7, background: 'rgba(7,18,30,0.9)', borderLeft: `1px solid ${c.main}33`, borderRight: `1px solid ${c.main}33` }} />

          {/* Body + Arms */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
            {[-1, 1].map(side => (
              <div key={side} style={{
                position: 'absolute', top: 6,
                [side === -1 ? 'left' : 'right']: -16,
                width: 13, height: 64,
                background: 'rgba(8,20,32,0.9)',
                border: `1px solid ${c.main}28`,
                borderRadius: 7,
                display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
                paddingBottom: 4,
              }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 5px ${color}` }} />
              </div>
            ))}

            {/* Torso */}
            <div style={{
              width: 96, height: 92,
              background: 'linear-gradient(150deg, #071827, #0b2237)',
              border: `1.5px solid ${c.main}44`,
              borderRadius: 14,
              position: 'relative', overflow: 'hidden',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <div style={{ position: 'absolute', left: 0, right: 0, height: 1, background: `${c.main}28`, animation: 'roScan 3s linear infinite 1s' }} />

              {/* Shoulder lights */}
              {[-1, 1].map(s => (
                <div key={s} style={{
                  position: 'absolute', top: 14,
                  [s === -1 ? 'left' : 'right']: 8,
                  width: 5, height: 5, borderRadius: '50%',
                  background: color,
                  boxShadow: `0 0 6px ${color}`,
                }} />
              ))}

              {/* Arc reactor */}
              <div style={{ position: 'relative', width: 42, height: 42, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{
                  position: 'absolute', inset: 0, borderRadius: '50%',
                  borderWidth: 2, borderStyle: 'solid', borderColor: c.main, borderTopColor: 'transparent',
                  animation: `roReactor ${effState === 'thinking' ? '0.9s' : '2.2s'} linear infinite`,
                }} />
                <div style={{
                  position: 'absolute', inset: 6, borderRadius: '50%',
                  borderWidth: 1.5, borderStyle: 'solid', borderColor: `${c.main}55`, borderBottomColor: 'transparent',
                  animation: 'roSpinSlow 1.6s linear infinite',
                }} />
                <div style={{
                  width: 15, height: 15, borderRadius: '50%',
                  background: `radial-gradient(circle, #fff 0%, ${color} 45%, transparent 80%)`,
                  boxShadow: `0 0 12px ${color}, 0 0 24px ${color}66`,
                }} />
              </div>

              {/* Chest lines */}
              <div style={{ position: 'absolute', bottom: 10, left: 10, right: 10, display: 'flex', flexDirection: 'column', gap: 3 }}>
                {[1, 0.55, 0.28].map((o, i) => (
                  <div key={i} style={{ height: 1, background: c.main, opacity: o, borderRadius: 1 }} />
                ))}
              </div>
            </div>
          </div>

          {/* Legs */}
          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            {[0, 1].map(i => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                <div style={{ width: 18, height: 32, background: 'rgba(8,20,32,0.9)', border: `1px solid ${c.main}28`, borderRadius: 6 }} />
                <div style={{ width: 24, height: 8, background: 'rgba(8,20,32,0.9)', border: `1px solid ${c.main}33`, borderRadius: 4 }} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* State label */}
      <div style={{
        marginTop: 10,
        fontFamily: 'Orbitron, monospace',
        fontSize: 8.5, letterSpacing: 2,
        color: c.main, opacity: 0.85,
      }}>
        {LABELS[effState] || LABELS.idle}
      </div>
      <div style={{ fontSize: 9, color: 'rgba(56,189,248,0.35)', marginTop: 3, minHeight: 12 }}>
        {effState === 'idle' ? 'CLICK TO SPEAK' : ''}
      </div>
    </div>
  )
}
