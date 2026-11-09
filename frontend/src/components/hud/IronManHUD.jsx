// IronManHUD.jsx — Full Iron Man style UI
import { useState, useEffect } from 'react'
import useAtlasStore from '../../store/useAtlasStore'
import { lockSystem } from '../../services/api'
import HUDTopBar from './HUDTopBar'
import HUDLeft from './HUDLeft'
import HUDCenter from './HUDCenter'
import HUDRight from './HUDRight'
import HUDBottom from './HUDBottom'

export default function IronManHUD() {
  return (
    <div style={S.root}>
      {/* Scanline overlay */}
      <div style={S.scanline} />
      {/* Corner brackets */}
      <div style={{...S.corner, top:10, left:10, borderTop:'2px solid #00ffc8', borderLeft:'2px solid #00ffc8'}} />
      <div style={{...S.corner, top:10, right:10, borderTop:'2px solid #00ffc8', borderRight:'2px solid #00ffc8'}} />
      <div style={{...S.corner, bottom:10, left:10, borderBottom:'2px solid #00ffc8', borderLeft:'2px solid #00ffc8'}} />
      <div style={{...S.corner, bottom:10, right:10, borderBottom:'2px solid #00ffc8', borderRight:'2px solid #00ffc8'}} />

      <div style={S.grid}>
        <HUDTopBar />
        <HUDLeft />
        <HUDCenter />
        <HUDRight />
        <HUDBottom />
      </div>
    </div>
  )
}

const S = {
  root: { width:'100vw', height:'100vh', background:'#000c08', color:'#00ffc8', fontFamily:"'Share Tech Mono', monospace", position:'relative', overflow:'hidden' },
  scanline: { position:'fixed', inset:0, background:'repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 4px)', pointerEvents:'none', zIndex:9999 },
  corner: { position:'absolute', width:22, height:22, zIndex:10 },
  grid: { display:'grid', gridTemplateColumns:'190px 1fr 190px', gridTemplateRows:'48px 1fr 110px', gap:6, padding:10, height:'100vh', width:'100vw' },
}