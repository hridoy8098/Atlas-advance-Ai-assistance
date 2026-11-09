// HUDBottom.jsx — Prayer times + voice status + active panel content
import { useState } from 'react'
import useAtlasStore from '../../store/useAtlasStore'
import SystemPanel from '../panels/SystemPanel'
import AnalyticsPanel from '../panels/AnalyticsPanel'
import SecurityPanel from '../panels/SecurityPanel'
import StudyPanel from '../panels/StudyPanel'
import BangladeshPanel from '../panels/BangladeshPanel'

const PANEL_MAP = {
  system:     SystemPanel,
  analytics:  AnalyticsPanel,
  security:   SecurityPanel,
  study:      StudyPanel,
  bangladesh: BangladeshPanel,
}

export default function HUDBottom() {
  const { prayerTimes, activePanel } = useAtlasStore()
  const [voiceRunning, setVoiceRunning] = useState(false)

  const toggleVoice = async () => {
    try {
      const endpoint = voiceRunning ? '/api/voice/stop' : '/api/voice/start'
      await fetch(endpoint, { method:'POST' })
      setVoiceRunning(!voiceRunning)
    } catch {}
  }

  const prayers = [
    { name:'FAJR',    time: prayerTimes.fajr },
    { name:'DHUHR',   time: prayerTimes.dhuhr },
    { name:'ASR',     time: prayerTimes.asr },
    { name:'MAGHRIB', time: prayerTimes.maghrib },
    { name:'ISHA',    time: prayerTimes.isha },
  ]

  // If a non-chat panel is active, show it full bottom
  const PanelComp = activePanel !== 'chat' ? PANEL_MAP[activePanel] : null

  if (PanelComp) {
    return (
      <div style={{ gridColumn:'1/-1', background:'rgba(0,15,12,0.9)', border:'1px solid rgba(0,255,200,0.15)', borderRadius:6, padding:12, overflow:'auto' }}>
        <PanelComp />
      </div>
    )
  }

  return (
    <div style={S.bar}>
      {/* Prayer times */}
      <div style={S.prayerCard}>
        {prayers.map(p => (
          <div key={p.name} style={S.prayerItem}>
            <span style={S.prayerName}>{p.name}</span>
            <span style={S.prayerTime}>{p.time || '--:--'}</span>
          </div>
        ))}
      </div>

      {/* Voice toggle */}
      <button onClick={toggleVoice} style={{ ...S.voiceBtn, borderColor: voiceRunning ? 'rgba(255,100,0,0.5)' : 'rgba(0,255,200,0.2)', background: voiceRunning ? 'rgba(255,100,0,0.1)' : 'rgba(0,255,200,0.05)' }}>
        <style>{`@keyframes micP{0%,100%{opacity:1}50%{opacity:0.3}}`}</style>
        <div style={{ width:8, height:8, borderRadius:'50%', background: voiceRunning ? '#ff6600' : 'rgba(0,255,200,0.4)', animation: voiceRunning ? 'micP 1s ease-in-out infinite' : 'none', boxShadow: voiceRunning ? '0 0 8px #ff6600' : 'none' }} />
        <span style={{ fontFamily:'Orbitron,monospace', fontSize:9, letterSpacing:1, color: voiceRunning ? '#ff8833' : 'rgba(0,255,200,0.5)' }}>
          {voiceRunning ? 'VOICE ACTIVE — CLICK STOP' : 'ALWAYS-ON VOICE'}
        </span>
      </button>

      {/* Status */}
      <div style={S.statusCard}>
        <div style={{ fontSize:8, letterSpacing:2, color:'rgba(0,255,200,0.35)', marginBottom:4 }}>WAKE WORD</div>
        <div style={{ fontSize:13, color:'#00ffc8', fontFamily:'Orbitron,monospace', letterSpacing:3 }}>"ATLAS"</div>
        <div style={{ fontSize:8, color:'rgba(0,255,200,0.3)', marginTop:2 }}>{voiceRunning ? 'LISTENING...' : 'STANDBY'}</div>
      </div>
    </div>
  )
}

const S = {
  bar: { gridColumn:'1/-1', display:'flex', gap:6, alignItems:'stretch' },
  prayerCard: { flex:1, background:'rgba(0,20,16,0.75)', border:'1px solid rgba(0,255,200,0.18)', borderRadius:6, padding:'8px 16px', display:'flex', justifyContent:'space-around', alignItems:'center' },
  prayerItem: { display:'flex', flexDirection:'column', alignItems:'center', gap:3 },
  prayerName: { fontSize:8, color:'rgba(0,255,200,0.4)', letterSpacing:1 },
  prayerTime: { fontSize:13, color:'#00ffc8', fontFamily:'Share Tech Mono,monospace' },
  voiceBtn: { display:'flex', alignItems:'center', gap:10, padding:'0 20px', border:'1px solid', borderRadius:6, cursor:'pointer', fontFamily:'Share Tech Mono,monospace', minWidth:200 },
  statusCard: { background:'rgba(0,20,16,0.75)', border:'1px solid rgba(0,255,200,0.18)', borderRadius:6, padding:'8px 16px', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center' },
}