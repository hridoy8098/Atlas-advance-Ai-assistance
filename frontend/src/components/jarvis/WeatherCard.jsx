// WeatherCard.jsx — current weather with a compact details row.
import { useState } from 'react'
import { Cloud, CloudRain, CloudSnow, CloudSun, Droplets, RefreshCw, Sun, Thermometer, Wind } from 'lucide-react'
import { Panel, IconButton, MiniStat } from './ui'
import { T } from './theme'

function WeatherIcon({ desc, size = 46 }) {
  const d = String(desc || '').toLowerCase()
  const common = { size, color: T.accent, strokeWidth: 1.4, style: { opacity: 0.9, filter: 'drop-shadow(0 0 12px rgba(56,189,248,0.25))' } }
  if (d.includes('rain') || d.includes('drizzle')) return <CloudRain {...common} />
  if (d.includes('snow')) return <CloudSnow {...common} />
  if (d.includes('clear') || d.includes('sun')) return <Sun {...common} />
  if (d.includes('cloud')) return <Cloud {...common} />
  return <CloudSun {...common} />
}

export default function WeatherCard({ weather, onRefresh }) {
  const [spinning, setSpinning] = useState(false)
  const temp = Number(weather?.temp)
  const feels = Number(weather?.feels_like)
  const humidity = Number(weather?.humidity)
  const wind = Number(weather?.wind)

  const refresh = async () => {
    setSpinning(true)
    try {
      await onRefresh?.()
    } finally {
      setTimeout(() => setSpinning(false), 450)
    }
  }

  return (
    <Panel
      title="Weather"
      icon={CloudSun}
      action={
        <IconButton title="Refresh weather" onClick={refresh} disabled={spinning}>
          <RefreshCw size={14} className={spinning ? 'jv-spin' : ''} />
        </IconButton>
      }
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: T.font, fontSize: 28, fontWeight: 600, color: T.text, lineHeight: 1.05, letterSpacing: '-0.02em' }}>
            {Number.isFinite(temp) ? temp.toFixed(1) : '--'}
            <span style={{ fontSize: 15, color: T.muted, marginLeft: 3 }}>°C</span>
          </div>
          <div style={{ fontSize: 12, color: T.text, marginTop: 5 }}>{weather?.city || 'Dhaka'}</div>
          <div style={{ fontSize: 11, color: T.muted, marginTop: 2, textTransform: 'capitalize' }}>
            {weather?.desc || 'Partly cloudy'}
          </div>
        </div>
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: 16,
            flexShrink: 0,
            display: 'grid',
            placeItems: 'center',
            background: 'radial-gradient(circle at 50% 38%, rgba(56,189,248,0.16), rgba(56,189,248,0.03) 72%)',
            border: '1px solid rgba(56,189,248,0.14)',
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04)',
          }}
        >
          <WeatherIcon desc={weather?.desc} size={38} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 7, marginTop: 10 }}>
        <MiniStat
          label="Humidity"
          value={`${Number.isFinite(humidity) ? humidity : '--'}%`}
          color="#22d3ee"
        />
        <MiniStat
          label="Wind"
          value={`${Number.isFinite(wind) ? wind.toFixed(1) : '--'} m/s`}
          color="#a5b4fc"
        />
        <MiniStat
          label="Feels Like"
          value={`${Number.isFinite(feels) ? feels.toFixed(1) : Number.isFinite(temp) ? temp.toFixed(1) : '--'} °C`}
          color="#fbbf24"
        />
      </div>
    </Panel>
  )
}
