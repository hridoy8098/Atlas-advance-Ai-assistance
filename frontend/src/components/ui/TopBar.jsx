// TopBar.jsx
import { useState, useEffect } from 'react'
import useAtlasStore from '../../store/useAtlasStore'

export default function TopBar() {
  const { weather, metrics, userName } = useAtlasStore()
  const [time, setTime] = useState(new Date())
  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t) }, [])

  const timeStr = time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  const dateStr = time.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

  return (
    <div style={S.bar}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: 'Orbitron', fontSize: 14, color: 'var(--cyan)', textShadow: '0 0 10px var(--cyan)' }}>ATLAS 7.0</span>
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>/ {userName}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <span style={{ fontFamily: 'Share Tech Mono', fontSize: 20, color: 'var(--cyan)' }}>{timeStr}</span>
        <span style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2 }}>{dateStr}</span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <Chip label="CPU" value={metrics.cpu + '%'} warn={metrics.cpu > 80} />
        <Chip label="RAM" value={metrics.mem_percent + '%'} warn={metrics.mem_percent > 85} />
        <Chip label={weather.city} value={Math.round(weather.temp) + '°C'} />
        {metrics.bat_percent > 0 && <Chip label={metrics.bat_charging ? '⚡' : '🔋'} value={Math.round(metrics.bat_percent) + '%'} />}
      </div>
    </div>
  )
}

function Chip({ label, value, warn }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '3px 8px', border: '1px solid', borderColor: warn ? 'rgba(255,100,0,0.5)' : 'var(--cyan-border)', borderRadius: 6, background: 'rgba(0,255,255,0.04)' }}>
      <span style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: 1 }}>{label}</span>
      <span style={{ fontSize: 11, color: warn ? '#ff8844' : 'var(--cyan)', fontFamily: 'Share Tech Mono' }}>{value}</span>
    </div>
  )
}

const S = {
  bar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', borderBottom: '1px solid var(--cyan-border)', background: 'rgba(0,10,20,0.6)', backdropFilter: 'blur(10px)', height: 52, flexShrink: 0 },
}
