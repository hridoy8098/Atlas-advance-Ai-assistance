// Sidebar.jsx
import { motion } from 'framer-motion'
import useAtlasStore from '../../store/useAtlasStore'

const NAV = [
  { id: 'chat',       icon: '💬', label: 'CHAT' },
  { id: 'system',     icon: '💻', label: 'SYSTEM' },
  { id: 'analytics',  icon: '📊', label: 'ANALYTICS' },
  { id: 'security',   icon: '🔐', label: 'SECURITY' },
  { id: 'study',      icon: '📚', label: 'STUDY' },
  { id: 'media',      icon: '🎵', label: 'MEDIA' },
  { id: 'bangladesh', icon: '🇧🇩', label: 'BD' },
]

export default function Sidebar() {
  const { activePanel, setActivePanel, logout } = useAtlasStore()

  const handleLock = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
    } catch {}
    logout()
    window.location.href = '/login'
  }

  return (
    <div style={S.sidebar}>
      <div style={S.logo}>
        <span style={S.logoA}>A</span>
        <span style={S.logoVer}>7.0</span>
      </div>
      <nav style={S.nav}>
        {NAV.map(item => (
          <motion.button key={item.id} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            onClick={() => setActivePanel(item.id)}
            title={item.label}
            style={{ ...S.navBtn,
              background: activePanel === item.id ? 'rgba(0,255,200,0.12)' : 'transparent',
              borderLeft: activePanel === item.id ? '2px solid var(--cyan)' : '2px solid transparent',
              color: activePanel === item.id ? 'var(--cyan)' : 'var(--text-dim)',
            }}>
            <span style={{ fontSize: 18 }}>{item.icon}</span>
            <span style={{ fontSize: 9, letterSpacing: 1, fontWeight: 600 }}>{item.label}</span>
          </motion.button>
        ))}
      </nav>
      <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
        onClick={handleLock} style={S.lockBtn} title="Lock">
        <span>🔒</span>
        <span style={{ fontSize: 9, letterSpacing: 1 }}>LOCK</span>
      </motion.button>
    </div>
  )
}

const S = {
  sidebar: { width: 72, height: '100vh', background: 'rgba(0,10,20,0.95)', borderRight: '1px solid var(--cyan-border)', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '12px 0', flexShrink: 0 },
  logo: { marginBottom: 24, textAlign: 'center' },
  logoA: { display: 'block', fontFamily: 'Orbitron', fontSize: 22, color: 'var(--cyan)', textShadow: '0 0 15px var(--cyan)' },
  logoVer: { fontSize: 9, color: 'var(--text-dim)', letterSpacing: 1 },
  nav: { flex: 1, display: 'flex', flexDirection: 'column', gap: 4, width: '100%', padding: '0 6px' },
  navBtn: { width: '100%', padding: '10px 6px', border: 'none', borderRadius: 6, cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, transition: 'all 0.2s', fontFamily: 'Rajdhani' },
  lockBtn: { width: 'calc(100% - 12px)', padding: '10px 6px', border: '1px solid rgba(255,68,68,0.3)', borderRadius: 6, background: 'rgba(255,68,68,0.08)', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, color: '#ff6666', fontFamily: 'Rajdhani', transition: 'all 0.2s' },
}
