// ServerSetup.jsx — pair the phone app with the Atlas server on the laptop.
import { useEffect, useState } from 'react'
import { Check, Loader2, Laptop, Link2, WifiOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { checkServer, getConnectorPairing, getServerUrl, isNativeApp, setServerUrl } from '../../services/api'
import { T } from './theme'

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  background: 'rgba(4,11,19,0.9)',
  border: `1px solid ${T.border}`,
  borderRadius: 8,
  color: T.text,
  padding: '10px 11px',
  fontSize: 12,
  outline: 'none',
}

export default function ServerSetup({ blocking = false, onClose, onConnected }) {
  const [url, setUrl] = useState(getServerUrl() || 'http://')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [pairing, setPairing] = useState(null)

  useEffect(() => {
    if (blocking) {
      const guess = getServerUrl()
      if (guess) setUrl(guess)
    }
  }, [blocking])

  useEffect(() => {
    if (getServerUrl()) {
      getConnectorPairing().then(setPairing).catch(() => setPairing(null))
    }
  }, [])

  const connect = async () => {
    let value = url.trim().replace(/\/+$/, '')
    if (!value.startsWith('http://') && !value.startsWith('https://')) {
      value = `http://${value}`
    }
    setStatus('testing')
    setError('')
    try {
      await checkServer(value)
      setServerUrl(value)
      setStatus('ok')
      toast.success('Laptop connected')
      setTimeout(() => {
        onConnected?.(value)
        if (blocking) window.location.reload()
        else onClose?.()
      }, 450)
    } catch (e) {
      setStatus('error')
      setError('Server পাওয়া যায়নি। URL সঠিক কিনা এবং server চালু আছে কিনা দেখুন।')
    }
  }

  const content = (
    <div
      style={{
        width: 380,
        maxWidth: 'calc(100vw - 28px)',
        borderRadius: 14,
        background: 'linear-gradient(180deg, rgba(13,27,42,0.99), rgba(8,17,28,0.99))',
        border: `1px solid ${T.border}`,
        boxShadow: '0 28px 70px rgba(0,0,0,0.65)',
        padding: 18,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: T.accentSoft, border: '1px solid rgba(56,189,248,0.25)',
        }}>
          <Laptop size={17} color={T.accent} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text }}>Connect Atlas server</div>
          <div style={{ fontSize: 10, color: T.muted, marginTop: 1 }}>Cloud URL or same WiFi</div>
        </div>
        <Link2 size={15} color={T.dim} />
      </div>

      <div style={{ fontSize: 10.5, color: T.muted, lineHeight: 1.5, margin: '10px 0 12px' }}>
        Backend-এর URL দিন। Cloud deployment হলে Render URL, নইলে laptop-এ{' '}
        <span style={{ color: T.text, fontFamily: T.mono }}>python server.py</span> চালিয়ে WiFi IP,
        যেমন <span style={{ color: T.text, fontFamily: T.mono }}>http://192.168.0.5:8000</span>।
      </div>

      <label style={{ fontSize: 9.5, color: T.dim, display: 'block', marginBottom: 5, letterSpacing: '0.08em' }}>
        ATLAS SERVER URL
      </label>
      <input
        value={url}
        onChange={e => setUrl(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') connect() }}
        placeholder="https://atlas-7-api.onrender.com"
        style={inputStyle}
        autoCapitalize="none"
        autoCorrect="off"
        spellCheck={false}
      />

      {status === 'error' && (
        <div style={{ display: 'flex', gap: 6, marginTop: 9, color: '#fca5a5', fontSize: 10.5, lineHeight: 1.45 }}>
          <WifiOff size={13} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{error}</span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 7, marginTop: 14 }}>
        <button
          type="button"
          onClick={connect}
          disabled={status === 'testing' || status === 'ok'}
          style={{
            flex: 1, padding: '9px 12px', borderRadius: 8, cursor: 'pointer',
            border: '1px solid rgba(56,189,248,0.4)',
            background: 'rgba(56,189,248,0.14)', color: '#c9edff',
            fontSize: 11.5, fontWeight: 600,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}
        >
          {status === 'testing' && <Loader2 size={13} className="jv-spin" />}
          {status === 'ok' && <Check size={13} />}
          {status === 'testing' ? 'Connecting...' : status === 'ok' ? 'Connected' : 'Connect'}
        </button>
        {!blocking && (
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '9px 12px', borderRadius: 8, cursor: 'pointer',
              border: `1px solid ${T.border}`, background: 'transparent',
              color: T.muted, fontSize: 11.5,
            }}
          >
            Cancel
          </button>
        )}
      </div>

      <div style={{ marginTop: 10, fontSize: 9.5, color: T.dim, lineHeight: 1.5 }}>
        {isNativeApp()
          ? 'Phone app · PC agents will execute on the paired laptop.'
          : 'Web build · paste the backend URL (Render cloud or your laptop).'}
      </div>

      {pairing?.pairing_code && (
        <div style={{ marginTop: 8, padding: '7px 8px', borderRadius: 7, background: 'rgba(3,9,16,0.7)', border: `1px solid ${T.borderSoft}` }}>
          <div style={{ fontSize: 9, color: T.dim, letterSpacing: '0.08em', marginBottom: 3 }}>LAPTOP PAIRING CODE</div>
          <div style={{ fontSize: 10.5, color: T.accent, fontFamily: T.mono, wordBreak: 'break-all' }}>{pairing.pairing_code}</div>
          <div style={{ fontSize: 9, color: T.muted, lineHeight: 1.45, marginTop: 4 }}>
            Laptop-এ চালান: <span style={{ fontFamily: T.mono, color: T.text }}>python connector/atlas_laptop.py --server {getServerUrl() || 'http://localhost:8000'} --token {pairing.pairing_code}</span>
          </div>
        </div>
      )}
      {pairing?.from_env && (
        <div style={{ marginTop: 8, fontSize: 9, color: T.muted, lineHeight: 1.45 }}>
          Pairing token is set by <span style={{ fontFamily: T.mono, color: T.text }}>ATLAS_PAIR_TOKEN</span> on the server. Run the laptop connector with the same token.
        </div>
      )}
    </div>
  )

  if (blocking) {
    return (
      <div style={{
        position: 'fixed', inset: 0, zIndex: 500,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'radial-gradient(circle at 50% 30%, rgba(10,30,50,0.96), rgba(2,7,12,0.98))',
        padding: 14,
      }}>
        {content}
      </div>
    )
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 500,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(2,7,12,0.7)', padding: 14,
    }} onClick={e => { if (e.target === e.currentTarget) onClose?.() }}>
      {content}
    </div>
  )
}
