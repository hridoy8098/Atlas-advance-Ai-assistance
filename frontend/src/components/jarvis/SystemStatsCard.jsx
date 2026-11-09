// SystemStatsCard.jsx — CPU / RAM / disk overview.
import { useState } from 'react'
import { Cpu, RefreshCw } from 'lucide-react'
import { Panel, IconButton, Bar, MiniStat } from './ui'
import { T } from './theme'

export default function SystemStatsCard({ metrics, onRefresh }) {
  const [spinning, setSpinning] = useState(false)

  const cpu = Math.round(Number(metrics?.cpu) || 0)
  const ram = Math.round(Number(metrics?.mem_percent) || 0)
  const memGb = ((Number(metrics?.mem_used) || 0) / 1024).toFixed(1)
  const diskPct = Math.round(Number(metrics?.disk_percent) || 0)
  const diskUsed = Number(metrics?.disk_used_gb)
  const diskTotal = Number(metrics?.disk_total_gb)
  const hasDisk = Number.isFinite(diskUsed) && Number.isFinite(diskTotal) && diskTotal > 0
  const hasMetrics = Number.isFinite(Number(metrics?.cpu)) && Number.isFinite(Number(metrics?.mem_percent))

  const refresh = async () => {
    setSpinning(true)
    try {
      await onRefresh?.()
    } finally {
      setTimeout(() => setSpinning(false), 450)
    }
  }

  const cpuColor = !hasMetrics ? T.dim : cpu >= 80 ? T.red : T.accent
  const ramColor = !hasMetrics ? T.dim : ram >= 85 ? T.red : '#22d3ee'
  const diskColor = !hasMetrics ? T.dim : diskPct >= 90 ? T.red : '#818cf8'

  return (
    <Panel
      title="System Stats"
      icon={Cpu}
      action={
        <IconButton title="Refresh system stats" onClick={refresh} disabled={spinning}>
          <RefreshCw size={14} className={spinning ? 'jv-spin' : ''} />
        </IconButton>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: T.muted }}>CPU Usage</span>
            <span style={{ fontFamily: T.mono, fontSize: 12, color: T.text }}>{hasMetrics ? `${cpu}%` : '--'}</span>
          </div>
          <Bar value={hasMetrics ? cpu : 0} color={cpuColor} />
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: T.muted }}>RAM Usage</span>
            <span style={{ fontFamily: T.mono, fontSize: 12, color: T.text }}>{hasMetrics ? `${memGb} GB` : '--'}</span>
          </div>
          <Bar value={hasMetrics ? ram : 0} color={ramColor} />
        </div>

        <div style={{ display: 'flex', gap: 7, marginTop: 1 }}>
          <MiniStat label="CPU" value={hasMetrics ? `${cpu}%` : '--'} color={cpuColor} />
          <MiniStat label="Memory" value={hasMetrics ? `${ram}%` : '--'} color={ramColor} />
          <MiniStat
            label="Disk"
            value={hasDisk ? `${Math.round(diskUsed)}/${Math.round(diskTotal)} GB` : hasMetrics ? `${diskPct}%` : '--'}
            color={diskColor}
          />
        </div>
      </div>
    </Panel>
  )
}
