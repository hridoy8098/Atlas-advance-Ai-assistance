// SystemPanel.jsx
import { useState } from 'react'
import { motion } from 'framer-motion'
import useAtlasStore from '../../store/useAtlasStore'
import { optimizePC, cleanTemp, executeCommand } from '../../services/api'

export default function SystemPanel() {
  const { metrics } = useAtlasStore()
  const [log, setLog] = useState([])
  const [loading, setLoading] = useState(false)

  const addLog = (msg) => setLog(l => [...l, { id: Date.now(), msg, time: new Date().toLocaleTimeString() }])

  const runOptimize = async () => {
    setLoading(true); addLog('⚙️ Optimizing PC...')
    try { const r = await optimizePC(); addLog(`✅ Freed ${r.freed_mb?.toFixed(0) || '?'} MB`) }
    catch { addLog('❌ Optimize failed') }
    setLoading(false)
  }

  const runClean = async () => {
    setLoading(true); addLog('🧹 Cleaning temp files...')
    try { const r = await cleanTemp(); addLog(`✅ Cleaned ${r.freed_mb?.toFixed(0) || '?'} MB`) }
    catch { addLog('❌ Clean failed') }
    setLoading(false)
  }

  const bars = [
    { label: 'CPU', value: metrics.cpu, color: metrics.cpu > 80 ? '#ff5533' : '#00ffc8' },
    { label: 'RAM', value: metrics.mem_percent, color: metrics.mem_percent > 85 ? '#ff5533' : '#00aaff' },
    { label: 'DISK', value: metrics.disk_percent, color: metrics.disk_percent > 90 ? '#ff5533' : '#ff88ff' },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12, height: '100%' }}>
      {/* Meters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
        {bars.map(b => (
          <div key={b.label} style={S.card}>
            <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>{b.label}</div>
            <div style={{ fontFamily: 'Share Tech Mono', fontSize: 28, color: b.color, marginBottom: 8 }}>{b.value}<span style={{ fontSize: 12 }}>%</span></div>
            <div style={S.barBg}>
              <motion.div animate={{ width: `${b.value}%` }} transition={{ duration: 0.5 }}
                style={{ ...S.barFill, background: b.color, boxShadow: `0 0 8px ${b.color}` }} />
            </div>
          </div>
        ))}
      </div>

      {/* Actions + Log */}
      <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { label: '⚙️ Optimize PC', action: runOptimize },
            { label: '🧹 Clean Temp', action: runClean },
          ].map(btn => (
            <motion.button key={btn.label} whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
              onClick={btn.action} disabled={loading} style={S.btn}>{btn.label}</motion.button>
          ))}
          {metrics.bat_percent > 0 && (
            <div style={S.card}>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4 }}>BATTERY</div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 20, color: metrics.bat_charging ? '#00ff88' : 'var(--cyan)' }}>
                {metrics.bat_charging ? '⚡' : '🔋'} {Math.round(metrics.bat_percent)}%
              </div>
            </div>
          )}
        </div>

        {/* Log */}
        <div style={{ ...S.card, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ fontFamily: 'Orbitron', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 6 }}>SYSTEM LOG</div>
          {log.length === 0 && <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>No actions yet...</div>}
          {log.map(l => (
            <div key={l.id} style={{ fontSize: 12, fontFamily: 'Share Tech Mono', color: '#a0d0c0' }}>
              <span style={{ color: 'var(--text-dim)', marginRight: 8 }}>{l.time}</span>{l.msg}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const S = {
  card: { background: 'rgba(0,20,16,0.7)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 10, padding: 14 },
  barBg: { height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 2 },
  btn: { background: 'rgba(0,255,200,0.08)', border: '1px solid rgba(0,255,200,0.25)', borderRadius: 8, padding: '10px 14px', color: 'var(--cyan)', fontFamily: 'Rajdhani', fontSize: 13, cursor: 'pointer', textAlign: 'left', width: '100%' },
}
