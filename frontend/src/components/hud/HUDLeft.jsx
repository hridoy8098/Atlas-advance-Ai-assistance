// HUDLeft.jsx — System metrics + weather
import { motion } from 'framer-motion'
import useAtlasStore from '../../store/useAtlasStore'

function Card({ title, children, style }) {
  return (
    <div style={{ ...S.card, ...style }}>
      <div style={S.cardLine} />
      {title && <div style={S.cardTitle}>{title}</div>}
      {children}
    </div>
  )
}

function MetricBar({ label, value, color = '#00ffc8' }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
        <span style={{ fontSize:8, letterSpacing:2, color:'rgba(0,255,200,0.45)' }}>{label}</span>
        <span style={{ fontSize:11, color }}>{value}%</span>
      </div>
      <div style={S.barBg}>
        <motion.div animate={{ width: `${value}%` }} transition={{ duration:0.6 }}
          style={{ ...S.barFill, background:color, boxShadow:`0 0 6px ${color}` }} />
      </div>
    </div>
  )
}

export default function HUDLeft() {
  const { metrics, weather } = useAtlasStore()

  return (
    <div style={S.panel}>
      <Card title="PROCESSOR">
        <MetricBar label="CPU USAGE" value={Math.round(metrics.cpu)} color={metrics.cpu > 80 ? '#ff5533' : '#00ffc8'} />
      </Card>
      <Card title="MEMORY">
        <MetricBar label="RAM USAGE" value={Math.round(metrics.mem_percent)} color={metrics.mem_percent > 85 ? '#ff5533' : '#00aaff'} />
      </Card>
      <Card title="STORAGE">
        <MetricBar label="DISK USAGE" value={Math.round(metrics.disk_percent)} color={metrics.disk_percent > 90 ? '#ff5533' : '#ff88ff'} />
      </Card>

      {metrics.bat_percent > 0 && (
        <Card title="POWER CELL">
          <div style={{ fontSize:20, color: metrics.bat_charging ? '#00ff88' : '#00ffc8' }}>
            {metrics.bat_charging ? '⚡' : '🔋'} {Math.round(metrics.bat_percent)}<span style={{ fontSize:11 }}>%</span>
          </div>
          <div style={S.barBg}>
            <div style={{ ...S.barFill, width:`${metrics.bat_percent}%`, background: metrics.bat_charging ? '#00ff88' : '#00ffc8' }} />
          </div>
        </Card>
      )}

      <Card title={`WEATHER · ${weather.city?.toUpperCase()}`} style={{ flex:1 }}>
        <div style={{ fontSize:26, color:'#00ffc8', lineHeight:1 }}>{Math.round(weather.temp)}<span style={{ fontSize:12 }}>°C</span></div>
        <div style={{ fontSize:9, color:'rgba(0,255,200,0.5)', marginTop:4, textTransform:'uppercase', letterSpacing:1 }}>{weather.desc}</div>
        <div style={{ display:'flex', gap:12, marginTop:8 }}>
          <span style={{ fontSize:9, color:'rgba(0,255,200,0.4)' }}>HUM {weather.humidity}%</span>
          <span style={{ fontSize:9, color:'rgba(0,255,200,0.4)' }}>WIND {weather.wind} m/s</span>
        </div>
      </Card>
    </div>
  )
}

const S = {
  panel: { display:'flex', flexDirection:'column', gap:6 },
  card: { background:'rgba(0,20,16,0.75)', border:'1px solid rgba(0,255,200,0.18)', borderRadius:6, padding:'10px 12px', position:'relative', overflow:'hidden' },
  cardLine: { position:'absolute', top:0, left:0, right:0, height:1, background:'linear-gradient(90deg,transparent,rgba(0,255,200,0.35),transparent)' },
  cardTitle: { fontSize:8, letterSpacing:2, color:'rgba(0,255,200,0.4)', marginBottom:8 },
  barBg: { height:3, background:'rgba(0,255,200,0.08)', borderRadius:2, overflow:'hidden' },
  barFill: { height:'100%', borderRadius:2, transition:'width 0.5s' },
}