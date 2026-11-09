// HUDTopBar.jsx
import { useState, useEffect } from 'react'
import useAtlasStore from '../../store/useAtlasStore'
import { lockSystem } from '../../services/api'

export default function HUDTopBar() {
  const { userName, logout } = useAtlasStore()
  const [time, setTime] = useState(new Date())
  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t) }, [])

  const handleLock = async () => {
    try { await lockSystem() } catch {}
    logout()
    window.location.href = '/login'
  }

  return (
    <div style={S.bar}>
      <div style={S.left}>
        <span style={S.title}>ATLAS 7.0</span>
        <span style={S.sub}>/ A.I. CORE</span>
        <span style={S.sub}>/ {userName}</span>
      </div>
      <div style={S.center}>
        <span style={S.clock}>{time.toLocaleTimeString('en-US', { hour12: false })}</span>
        <span style={S.date}>{time.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
      </div>
      <div style={S.right}>
        <span style={S.online}>● SYSTEM ONLINE</span>
        <button onClick={handleLock} style={S.lockBtn}>🔒 LOCK</button>
      </div>
    </div>
  )
}

const S = {
  bar: { gridColumn:'1/-1', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 12px', borderBottom:'1px solid rgba(0,255,200,0.2)', background:'rgba(0,10,8,0.8)' },
  left: { display:'flex', alignItems:'center', gap:10 },
  title: { fontFamily:'Orbitron,monospace', fontSize:15, letterSpacing:4, color:'#00ffc8', textShadow:'0 0 12px rgba(0,255,200,0.5)' },
  sub: { fontSize:10, color:'rgba(0,255,200,0.45)', letterSpacing:1 },
  center: { display:'flex', flexDirection:'column', alignItems:'center' },
  clock: { fontFamily:'Share Tech Mono,monospace', fontSize:22, color:'#00ffc8' },
  date: { fontSize:9, color:'rgba(0,255,200,0.45)', letterSpacing:2 },
  right: { display:'flex', alignItems:'center', gap:14 },
  online: { fontSize:10, color:'#00ff88', letterSpacing:2 },
  lockBtn: { background:'rgba(255,50,50,0.1)', border:'1px solid rgba(255,50,50,0.3)', borderRadius:4, padding:'4px 10px', color:'#ff6666', fontFamily:'Share Tech Mono,monospace', fontSize:9, letterSpacing:1, cursor:'pointer' },
}