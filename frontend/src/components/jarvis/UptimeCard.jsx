// UptimeCard.jsx — compact PC uptime, session, command and load summary.
import { useEffect, useState } from 'react'
import { Activity } from 'lucide-react'
import { Panel, MiniStat } from './ui'
import { T } from './theme'

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [h, m, sec].map(v => String(v).padStart(2, '0')).join(':')
}

export default function UptimeCard({ metrics, sessionStart, commandCount }) {
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const uptime = Number(metrics?.uptime_seconds) || 0
  const hasMetrics = Number.isFinite(Number(metrics?.uptime_seconds))
  const uptimeLabel = hasMetrics ? formatDuration(uptime) : '--:--:--'
  const sessionSeconds = sessionStart ? (now - sessionStart) / 1000 : 0
  const load = Math.round(Number(metrics?.cpu) || 0)
  const loadColor = !hasMetrics ? T.dim : load >= 80 ? T.red : load >= 55 ? T.amber : T.accent

  return (
    <Panel
      title="System Uptime"
      icon={Activity}
      action={
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: T.green, boxShadow: `0 0 6px ${T.green}` }} />
          <span style={{ fontFamily: T.mono, fontSize: 10, color: T.muted }}>{uptimeLabel}</span>
        </div>
      }
    >
      <div style={{ display: 'flex', gap: 7 }}>
        <MiniStat label="Session" value={formatDuration(sessionSeconds)} color="#22d3ee" />
        <MiniStat label="Commands" value={String(commandCount || 0)} color={T.text} />
        <MiniStat label="Load" value={hasMetrics ? `${load}%` : '--'} color={loadColor} />
      </div>
    </Panel>
  )
}
