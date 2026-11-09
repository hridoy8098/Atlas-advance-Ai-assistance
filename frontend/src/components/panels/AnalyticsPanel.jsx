// AnalyticsPanel.jsx — real data from /api/analytics/*
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { getAnalyticsOverview } from '../../services/api'

export default function AnalyticsPanel() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getAnalyticsOverview(7)
      if (res?.success) setData(res)
      else setError(res?.error || 'Analytics unavailable')
    } catch (e) {
      setError(e.message || 'Analytics request failed')
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const cards = [
    { label: 'Productivity', value: data?.productivity ?? '—', unit: '%', color: '#00ffc8' },
    { label: 'Focus Score', value: data?.focus ?? '—', unit: '%', color: '#00aaff' },
    { label: 'Study Hours', value: data?.study_hours ?? '—', unit: 'h', color: '#ff88ff' },
    { label: 'Habit Streak', value: data?.habit_streak ?? '—', unit: 'd', color: '#ffaa00' },
  ]
  const series = data?.series || []

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12, height: '100%' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
        {cards.map(c => (
          <div key={c.label} style={S.card}>
            <div style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>{c.label.toUpperCase()}</div>
            <div style={{ fontFamily: 'Share Tech Mono', fontSize: 32, color: c.color }}>
              {c.value}<span style={{ fontSize: 14 }}>{c.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={S.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontFamily: 'Orbitron', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2 }}>WEEKLY PERFORMANCE</span>
          <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} onClick={load}
            style={S.refresh}>{loading ? 'LOADING…' : 'REFRESH'}</motion.button>
        </div>

        {error && <div style={{ fontSize: 11, color: '#ff6666', marginBottom: 8 }}>{error}</div>}

        {series.length === 0 && !loading ? (
          <div style={{ height: '80%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 12, textAlign: 'center' }}>
            No tracked activity yet.<br />Log a study session or use Atlas to start building your graph.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="85%">
            <LineChart data={series}>
              <XAxis dataKey="name" tick={{ fill: 'rgba(0,255,200,0.5)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: 'rgba(0,255,200,0.5)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#001020', border: '1px solid rgba(0,255,200,0.3)', borderRadius: 8, color: '#00ffc8' }} />
              <Line type="monotone" dataKey="productivity" stroke="#00ffc8" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="focus" stroke="#00aaff" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

const S = {
  card: { background: 'rgba(0,20,16,0.7)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 10, padding: 14 },
  refresh: { padding: '4px 12px', borderRadius: 6, border: '1px solid rgba(0,255,200,0.3)', background: 'rgba(0,255,200,0.08)', color: 'var(--cyan)', fontFamily: 'Rajdhani', fontSize: 10, letterSpacing: 1, cursor: 'pointer' },
}
