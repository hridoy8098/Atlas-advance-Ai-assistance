import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Eye, Wifi, Lock, Key, Bug } from 'lucide-react'
import {
  getSecurityOverview, scanMalware, checkBreach, checkPassword,
  setPrivacyMode, setFakeScreen, watermarkScreen, previewSelfDestruct,
} from '../../services/api'

export default function SecurityPanel() {
  const [activeTab, setActiveTab] = useState('overview')
  const [overview, setOverview] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [email, setEmail] = useState('')
  const [breachBusy, setBreachBusy] = useState(false)
  const [breach, setBreach] = useState(null)
  const [password, setPassword] = useState(null)
  const [privacy, setPrivacy] = useState(false)
  const [note, setNote] = useState('')
  const [error, setError] = useState(null)

  const loadOverview = async () => {
    try {
      const res = await getSecurityOverview()
      if (res?.success) {
        setOverview(res)
        setPrivacy(Boolean(res.privacy?.enabled))
      } else setError(res?.error || 'Security overview unavailable')
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => { loadOverview() }, [])

  const runScan = async () => {
    setScanning(true)
    setError(null)
    try {
      const res = await scanMalware(2000)
      if (res?.success) setScanResult(res)
      else setError(res?.error || 'Scan failed')
    } catch (e) {
      setError(e.message || 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  const runBreachCheck = async () => {
    if (!email.includes('@')) { setNote('Enter a valid email first'); return }
    setBreachBusy(true)
    try {
      const res = await checkBreach(email)
      setBreach(res)
    } catch (e) {
      setBreach({ available: false, message: e.message })
    } finally {
      setBreachBusy(false)
    }
  }

  const makePassword = async () => {
    try {
      const first = await checkPassword('')
      if (!first?.success) { setNote(first?.error || 'Password service unavailable'); return }
      const second = await checkPassword(first.password)
      setPassword({ password: first.password, strength: second.strength })
    } catch (e) {
      setNote(e.message)
    }
  }

  const togglePrivacy = async () => {
    const next = !privacy
    setPrivacy(next)
    try {
      const res = await setPrivacyMode(next)
      if (!res?.success) setNote(res?.error || 'Privacy toggle failed')
    } catch (e) {
      setNote(e.message)
    }
  }

  const toggleFakeScreen = async (show) => {
    try {
      const res = await setFakeScreen(show)
      setNote(res?.error ? res.error : `Fake screen ${show ? 'shown' : 'hidden'}`)
    } catch (e) {
      setNote(e.message)
    }
  }

  const captureWatermark = async () => {
    setNote('Capturing screen…')
    try {
      const res = await watermarkScreen('ATLAS')
      setNote(res?.success ? `Saved: ${res.output}` : (res?.error || 'Watermark failed'))
    } catch (e) {
      setNote(e.message)
    }
  }

  const previewWipe = async () => {
    try {
      const res = await previewSelfDestruct()
      setNote(res?.success ? `Dry run: ${res.target_count} file(s) would be deleted` : (res?.error || 'Preview failed'))
    } catch (e) {
      setNote(e.message)
    }
  }

  const net = overview?.network || {}
  const twoFA = overview?.two_fa || {}
  const scanBadge = scanResult
    ? (scanResult.suspicious_count === 0 ? 'CLEAN' : `${scanResult.suspicious_count} SUSPICIOUS`)
    : 'READY'

  const tabs = [
    { id: 'overview', label: 'OVERVIEW', icon: Shield },
    { id: 'scan', label: 'MALWARE SCAN', icon: Bug },
    { id: 'network', label: 'NETWORK', icon: Wifi },
    { id: 'privacy', label: 'PRIVACY', icon: Eye },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12, height: '100%' }}>
      <div style={{ display: 'flex', gap: 6 }}>
        {tabs.map(tab => (
          <motion.button key={tab.id} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...S.tab,
              background: activeTab === tab.id ? 'rgba(0,255,200,0.1)' : 'transparent',
              borderColor: activeTab === tab.id ? 'rgba(0,255,200,0.4)' : 'rgba(0,255,200,0.12)',
              color: activeTab === tab.id ? 'var(--cyan)' : 'var(--text-dim)',
            }}>
            <tab.icon size={14} />
            <span style={{ fontSize: 10, letterSpacing: 1 }}>{tab.label}</span>
          </motion.button>
        ))}
      </div>

      {(error || note) && (
        <div style={{ fontSize: 10, color: error ? '#ff6666' : 'rgba(0,255,200,0.7)' }}>{error || note}</div>
      )}

      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div key="overview" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={S.grid3}>
            <div style={S.card}>
              <div style={S.cardHead}><Shield size={18} color="#00ffc8" /><span style={S.cardLabel}>PROTECTION</span></div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 24, color: '#00ffc8' }}>{scanBadge}</div>
              <div style={S.sub}>{scanResult ? `${scanResult.files_scanned} files · ${scanResult.duration_ms}ms` : 'Run a scan to check'}</div>
            </div>

            <div style={S.card}>
              <div style={S.cardHead}><Lock size={18} color="#00aaff" /><span style={S.cardLabel}>AUTH</span></div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 24, color: '#00aaff' }}>{twoFA.enabled ? '2FA ON' : '2FA OFF'}</div>
              <div style={S.sub}>{twoFA.configured ? 'Secret configured' : 'Not configured yet'}</div>
            </div>

            <div style={S.card}>
              <div style={S.cardHead}><Key size={18} color="#ff88ff" /><span style={S.cardLabel}>PASSWORDS</span></div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 20, color: '#ff88ff' }}>
                {password ? password.strength.label.toUpperCase() : 'GENERATE'}
              </div>
              <div style={S.sub}>{password ? `${password.strength.length} chars · ${password.strength.score}/100` : 'Create a strong password'}</div>
              <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
                onClick={makePassword} style={{ ...S.smallBtn, marginTop: 8 }}>Generate</motion.button>
            </div>

            <div style={S.card}>
              <div style={S.cardHead}><Wifi size={18} color="#ffaa00" /><span style={S.cardLabel}>NETWORK</span></div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 24, color: '#00ff88' }}>
                {net.error ? 'NO DATA' : `${net.established ?? 0} LIVE`}
              </div>
              <div style={S.sub}>{net.total ?? 0} total · {net.listening ?? 0} listening</div>
            </div>

            <div style={S.card}>
              <div style={S.cardHead}><Bug size={18} color="#ff5533" /><span style={S.cardLabel}>LAST SCAN</span></div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 20, color: '#ff5533' }}>
                {scanResult ? `${scanResult.suspicious_count} threats` : 'No scan yet'}
              </div>
              <div style={S.sub}>{scanResult ? `${scanResult.files_scanned} files in ${scanResult.duration_ms}ms` : 'Run a scan to check'}</div>
            </div>

            <div style={S.card}>
              <div style={S.cardHead}><Eye size={18} color="#ff6600" /><span style={S.cardLabel}>BREACH CHECK</span></div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 18, color: breach?.breached ? '#ff5533' : '#00ff88' }}>
                {breach ? (breach.available === false ? 'UNAVAILABLE' : breach.breached ? `${breach.count} BREACHES` : 'NO BREACHES') : 'NOT CHECKED'}
              </div>
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <input value={email} onChange={e => setEmail(e.target.value)} placeholder="email@example.com" style={S.input} />
                <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
                  onClick={runBreachCheck} disabled={breachBusy} style={S.smallBtn}>
                  {breachBusy ? '…' : 'Check'}
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'scan' && (
          <motion.div key="scan" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16, height: '100%', overflow: 'auto' }}>
            <div style={S.scanCircle}>
              {scanning ? (
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  style={{ width: 60, height: 60, borderRadius: '50%', border: '3px solid transparent', borderTopColor: '#00ffc8', borderRightColor: '#00aaff' }} />
              ) : scanResult ? (
                <div style={{ fontFamily: 'Orbitron', fontSize: 14, color: scanResult.suspicious_count === 0 ? '#00ff88' : '#ff5533', textAlign: 'center', padding: 8 }}>
                  {scanResult.suspicious_count === 0 ? 'CLEAN' : `${scanResult.suspicious_count} THREATS`}
                </div>
              ) : (
                <Bug size={32} color="var(--text-dim)" />
              )}
            </div>
            <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
              onClick={runScan} disabled={scanning}
              style={{ ...S.scanBtn, opacity: scanning ? 0.5 : 1 }}>
              {scanning ? 'SCANNING...' : scanResult ? 'SCAN AGAIN' : 'START SCAN'}
            </motion.button>
            {scanResult && (
              <>
                <div style={{ display: 'flex', gap: 24 }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: 22, color: '#00ffc8' }}>{scanResult.files_scanned}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>FILES</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: 22, color: '#00ffc8' }}>{scanResult.duration_ms}ms</div>
                    <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>DURATION</div>
                  </div>
                </div>
                <div style={{ width: '100%', maxWidth: 520, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {scanResult.suspicious?.length === 0 && (
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', textAlign: 'center' }}>No suspicious files found</div>
                  )}
                  {scanResult.suspicious?.map((item, i) => (
                    <div key={i} style={{ ...S.card, padding: 10 }}>
                      <div style={{ fontSize: 11, color: '#ff8866', wordBreak: 'break-all' }}>{item.path}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>{item.reason}</div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </motion.div>
        )}

        {activeTab === 'network' && (
          <motion.div key="network" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, height: '100%' }}>
            <div style={S.card}>
              <div style={{ ...S.cardLabel, marginBottom: 12 }}>NETWORK STATUS</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: net.error ? '#ff5533' : '#00ff88', boxShadow: `0 0 8px ${net.error ? '#ff5533' : '#00ff88'}` }} />
                <span style={{ fontFamily: 'Share Tech Mono', fontSize: 16, color: net.error ? '#ff5533' : '#00ff88' }}>
                  {net.error ? 'MONITOR ERROR' : 'CONNECTED'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{net.established ?? 0} established · {net.listening ?? 0} listening</div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{net.total ?? 0} total connections</div>
            </div>
            <div style={S.card}>
              <div style={{ ...S.cardLabel, marginBottom: 10 }}>TOP PROCESSES</div>
              {(net.top_processes || []).length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>No connection data</div>
              )}
              {(net.top_processes || []).map((p, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-dim)', marginBottom: 6 }}>
                  <span style={{ color: 'var(--cyan)' }}>{p.name}</span>
                  <span>{p.connections}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === 'privacy' && (
          <motion.div key="privacy" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%', overflow: 'auto' }}>
            <div style={S.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ ...S.cardLabel, color: 'var(--cyan)' }}>PRIVACY MODE</div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                    {privacy ? 'Enabled — mic listening paused' : 'Disabled'}
                  </div>
                </div>
                <div onClick={togglePrivacy} style={{
                  width: 44, height: 24, borderRadius: 12, cursor: 'pointer',
                  background: privacy ? 'rgba(0,255,200,0.3)' : 'rgba(255,255,255,0.1)',
                  position: 'relative', transition: 'background 0.3s',
                  border: `1px solid ${privacy ? 'rgba(0,255,200,0.5)' : 'transparent'}`,
                }}>
                  <motion.div animate={{ x: privacy ? 22 : 2 }}
                    style={{ width: 18, height: 18, borderRadius: '50%', background: privacy ? '#00ffc8' : '#666', marginTop: 2 }} />
                </div>
              </div>
            </div>

            <div style={S.card}>
              <div style={{ ...S.cardLabel, color: 'var(--cyan)' }}>FAKE SCREEN</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', margin: '4px 0 8px' }}>Show a decoy fullscreen overlay</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={() => toggleFakeScreen(true)} style={S.smallBtn}>SHOW</motion.button>
                <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={() => toggleFakeScreen(false)}
                  style={{ ...S.smallBtn, background: 'rgba(255,80,80,0.08)', borderColor: 'rgba(255,80,80,0.3)', color: '#ff8888' }}>HIDE</motion.button>
              </div>
            </div>

            <div style={S.card}>
              <div style={{ ...S.cardLabel, color: 'var(--cyan)' }}>SCREEN WATERMARK</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', margin: '4px 0 8px' }}>Capture the screen with an ATLAS watermark</div>
              <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={captureWatermark} style={S.smallBtn}>CAPTURE</motion.button>
            </div>

            <div style={S.card}>
              <div style={{ ...S.cardLabel, color: 'var(--cyan)' }}>SELF DESTRUCT</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', margin: '4px 0 8px' }}>
                Preview which data files would be wiped (dry run only)
              </div>
              <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={previewWipe}
                style={{ ...S.smallBtn, background: 'rgba(255,80,80,0.08)', borderColor: 'rgba(255,80,80,0.3)', color: '#ff8888' }}>PREVIEW</motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const S = {
  tab: { display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid', cursor: 'pointer', fontFamily: 'Rajdhani', fontSize: 12, background: 'transparent' },
  card: { background: 'rgba(0,20,16,0.7)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 10, padding: 14 },
  grid3: { display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, overflow: 'auto' },
  cardHead: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 },
  cardLabel: { fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2 },
  sub: { fontSize: 11, color: 'rgba(0,255,200,0.5)', marginTop: 4 },
  input: { flex: 1, minWidth: 0, background: 'rgba(0,255,200,0.04)', border: '1px solid rgba(0,255,200,0.2)', borderRadius: 6, padding: '6px 8px', color: 'var(--cyan)', fontSize: 11, outline: 'none' },
  smallBtn: { padding: '6px 14px', borderRadius: 6, border: '1px solid rgba(0,255,200,0.3)', background: 'rgba(0,255,200,0.08)', color: 'var(--cyan)', fontFamily: 'Rajdhani', fontSize: 12, cursor: 'pointer' },
  scanCircle: { width: 120, height: 120, borderRadius: '50%', border: '2px solid rgba(0,255,200,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,20,16,0.7)' },
  scanBtn: { padding: '12px 32px', borderRadius: 8, border: '1px solid rgba(0,255,200,0.3)', background: 'rgba(0,255,200,0.1)', color: 'var(--cyan)', fontFamily: 'Orbitron', fontSize: 11, letterSpacing: 3, cursor: 'pointer' },
}
