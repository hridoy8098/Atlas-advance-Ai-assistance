// CameraCard.jsx — square webcam tile with a full-bleed live preview.
import { useEffect, useRef, useState } from 'react'
import { Power, Video, VideoOff } from 'lucide-react'
import { IconButton } from './ui'
import { T, panelStyle, titleStyle } from './theme'

export default function CameraCard({ active, onToggle }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [starting, setStarting] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!active) {
      streamRef.current?.getTracks().forEach(track => track.stop())
      streamRef.current = null
      if (videoRef.current) videoRef.current.srcObject = null
      setStarting(false)
      setStreaming(false)
      setError('')
      return
    }

    let cancelled = false

    const start = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('Camera API unavailable')
        return
      }
      setStarting(true)
      setStreaming(false)
      setError('')
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 1280 }, facingMode: 'user' },
          audio: false,
        })
        if (cancelled) {
          stream.getTracks().forEach(track => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          if (!cancelled) setStreaming(true)
          await videoRef.current.play().catch(() => {})
        } else if (!cancelled) {
          setStreaming(true)
        }
      } catch (err) {
        const name = err?.name || ''
        setError(
          name === 'NotAllowedError'
            ? 'Camera permission denied'
            : name === 'NotFoundError'
              ? 'No camera found'
              : 'Camera unavailable'
        )
      } finally {
        if (!cancelled) setStarting(false)
      }
    }

    start()

    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach(track => track.stop())
      streamRef.current = null
      if (videoRef.current) videoRef.current.srcObject = null
      setStreaming(false)
    }
  }, [active])

  const live = active && !error && streaming
  const statusText = error
    ? error
    : live
      ? 'Camera active — live preview'
      : starting
        ? 'Starting camera…'
        : 'Camera is inactive. Tap the power button to start.'
  const statusColor = error ? T.red : live ? '#86efac' : T.dim

  return (
    <section
      className="jv-panel"
      style={{
        ...panelStyle,
        position: 'relative',
        width: '100%',
        maxWidth: 360,
        aspectRatio: '1 / 1',
        flex: '0 0 auto',
        justifySelf: 'center',
        minHeight: 0,
      }}
    >
      {/* Feed / placeholder */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at 50% 44%, #081a2b 0%, #050d16 68%, #030810 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: 'scaleX(-1)',
            display: live ? 'block' : 'none',
          }}
        />

        {!live && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 9, padding: 20, textAlign: 'center' }}>
            {starting ? (
              <>
                <div
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: '50%',
                    border: `2px solid ${T.accent}`,
                    borderTopColor: 'transparent',
                    animation: 'jvSpin 0.9s linear infinite',
                  }}
                />
                <span style={{ fontSize: 11.5, color: T.muted }}>Starting camera…</span>
              </>
            ) : (
              <>
                <VideoOff size={34} color={error ? T.red : T.dim} strokeWidth={1.3} />
                <span style={{ fontSize: 12.5, color: error ? T.red : T.muted, fontWeight: 500 }}>
                  {error ? 'Camera unavailable' : 'Camera Off'}
                </span>
              </>
            )}
          </div>
        )}

        {live && (
          <div
            style={{
              position: 'absolute',
              top: 53,
              left: 13,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 9px',
              borderRadius: 999,
              background: 'rgba(3,7,13,0.72)',
              border: '1px solid rgba(34,197,94,0.35)',
              backdropFilter: 'blur(6px)',
            }}
          >
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: T.green, boxShadow: `0 0 6px ${T.green}` }} />
            <span style={{ fontFamily: T.mono, fontSize: 9, color: '#86efac', letterSpacing: '0.1em' }}>LIVE</span>
          </div>
        )}
      </div>

      {/* Header overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '12px 13px 24px',
          background: 'linear-gradient(180deg, rgba(5,11,20,0.92) 0%, rgba(5,11,20,0.44) 58%, transparent 100%)',
        }}
      >
        <Video size={15} color={T.accent} strokeWidth={1.8} />
        <span style={titleStyle}>Camera</span>
        <IconButton
          title={active ? 'Turn camera off' : 'Turn camera on'}
          active={active}
          onClick={onToggle}
          style={{
            background: active ? T.accentSoft : 'rgba(3,9,16,0.5)',
            borderColor: active ? 'rgba(56,189,248,0.35)' : 'rgba(56,189,248,0.14)',
            backdropFilter: 'blur(6px)',
          }}
        >
          <Power size={14} />
        </IconButton>
      </div>

      {/* Footer overlay */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 3,
          padding: '20px 13px 11px',
          background: 'linear-gradient(0deg, rgba(5,11,20,0.94) 0%, rgba(5,11,20,0.42) 62%, transparent 100%)',
        }}
      >
        <div
          style={{
            fontSize: 10.5,
            color: statusColor,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {statusText}
        </div>
      </div>
    </section>
  )
}
