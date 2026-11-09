// HUDRight.jsx — AI status + modules + nav
import { useState } from 'react'
import { motion } from 'framer-motion'
import useAtlasStore from '../../store/useAtlasStore'

const NAV_ITEMS = [
  { id:'chat',       icon:'💬', label:'CHAT' },
  { id:'system',     icon:'💻', label:'SYSTEM' },
  { id:'analytics',  icon:'📊', label:'ANALYTICS' },
  { id:'security',   icon:'🔐', label:'SECURITY' },
  { id:'study',      icon:'📚', label:'STUDY' },
  { id:'bangladesh', icon:'🇧🇩', label:'BD HUB' },
]

function Card({ title, children, style }) {
  return (
    <div style={{ background:'rgba(0,20,16,0.75)', border:'1px solid rgba(0,255,200,0.18)', borderRadius:6, padding:'10px 12px', position:'relative', overflow:'hidden', ...style }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:1, background:'linear-gradient(90deg,transparent,rgba(0,255,200,0.35),transparent)' }} />
      {title && <div style={{ fontSize:8, letterSpacing:2, color:'rgba(0,255,200,0.4)', marginBottom:8 }}>{title}</div>}
      {children}
    </div>
  )
}

export default function HUDRight() {
  const { activePanel, setActivePanel } = useAtlasStore()

  const modules = [
    { label:'Voice Engine', ok:true },
    { label:'Memory Core', ok:true },
    { label:'AI Engine', ok:true },
    { label:'PC Agent', ok:true },
    { label:'File Agent', ok:true },
    { label:'Face Auth', ok:false },
  ]

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
      {/* Navigation */}
      <Card title="NAVIGATION">
        <div style={{ display:'flex', flexDirection:'column', gap:3 }}>
          {NAV_ITEMS.map(item => (
            <motion.button key={item.id}
              whileHover={{ scale:1.02, x:2 }}
              whileTap={{ scale:0.97 }}
              onClick={() => setActivePanel(item.id)}
              style={{
                display:'flex', alignItems:'center', gap:8, padding:'6px 8px', borderRadius:5, border:'none', cursor:'pointer',
                background: activePanel === item.id ? 'rgba(0,255,200,0.12)' : 'transparent',
                borderLeft: `2px solid ${activePanel === item.id ? '#00ffc8' : 'transparent'}`,
                color: activePanel === item.id ? '#00ffc8' : 'rgba(0,255,200,0.45)',
                fontFamily:'Share Tech Mono,monospace', fontSize:10, letterSpacing:1, width:'100%', textAlign:'left',
              }}>
              <span style={{ fontSize:13 }}>{item.icon}</span>
              <span>{item.label}</span>
            </motion.button>
          ))}
        </div>
      </Card>

      {/* AI Model */}
      <Card title="AI ENGINE">
        <div style={{ fontSize:11, color:'#00ffc8', marginBottom:3 }}>GEMINI 3.8 FLASH</div>
        <div style={{ fontSize:9, color:'rgba(0,255,200,0.4)' }}>GROQ / LLAMA-3 BACKUP</div>
        <div style={{ display:'flex', alignItems:'center', gap:5, marginTop:6 }}>
          <div style={{ width:6, height:6, borderRadius:'50%', background:'#00ff88', boxShadow:'0 0 6px #00ff88' }} />
          <span style={{ fontSize:9, color:'#00ff88' }}>ALL KEYS ACTIVE</span>
        </div>
      </Card>

      {/* Modules */}
      <Card title="ACTIVE MODULES" style={{ flex:1 }}>
        <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
          {modules.map(m => (
            <div key={m.label} style={{ display:'flex', alignItems:'center', gap:6, fontSize:9 }}>
              <div style={{ width:5, height:5, borderRadius:'50%', background: m.ok ? '#00ff88' : 'rgba(255,200,0,0.7)', boxShadow: m.ok ? '0 0 5px #00ff88' : '0 0 5px rgba(255,200,0,0.5)', flexShrink:0 }} />
              <span style={{ color: m.ok ? 'rgba(0,255,200,0.7)' : 'rgba(255,200,0,0.6)', letterSpacing:0.5 }}>{m.label}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}