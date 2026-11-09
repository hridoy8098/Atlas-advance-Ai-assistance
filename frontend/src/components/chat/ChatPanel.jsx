// ChatPanel.jsx — Atlas 7.0 with 3D Robot + Voice + Agent System
import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useAtlasStore from '../../store/useAtlasStore'
import { sendCommand } from '../../services/api'

// ─── 3D CSS Robot ───────────────────────────────────────────
function AtlasRobot({ state, onClick }) {
  const colors = {
    idle:      { core: '#00ffc8', glow: 'rgba(0,255,200,0.4)', eye: '#00ffc8' },
    listening: { core: '#ff6600', glow: 'rgba(255,100,0,0.6)',  eye: '#ff8833' },
    thinking:  { core: '#8833ff', glow: 'rgba(136,51,255,0.6)', eye: '#aa66ff' },
    speaking:  { core: '#00aaff', glow: 'rgba(0,170,255,0.6)',  eye: '#33ccff' },
  }
  const c = colors[state] || colors.idle

  return (
    <div onClick={onClick} style={R.wrap} title="Click to speak">
      <style>{`
        @keyframes robotFloat { 0%,100%{transform:translateY(0) rotateY(0)}25%{transform:translateY(-6px) rotateY(4deg)}75%{transform:translateY(-3px) rotateY(-4deg)} }
        @keyframes eyePulse { 0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.8)} }
        @keyframes antennaPulse { 0%,100%{box-shadow:0 0 6px ${c.core},0 0 12px ${c.core}}50%{box-shadow:0 0 14px ${c.core},0 0 28px ${c.core}} }
        @keyframes coreRotate { from{transform:rotateZ(0)}to{transform:rotateZ(360deg)} }
        @keyframes listenRing { 0%{transform:scale(1);opacity:.8}100%{transform:scale(2.2);opacity:0} }
        @keyframes speakBar { 0%,100%{height:4px}50%{height:18px} }
      `}</style>

      {state === 'listening' && [0,1,2].map(i => (
        <div key={i} style={{
          position:'absolute', borderRadius:'50%', width:120, height:120,
          border:`2px solid ${c.core}`, animation:`listenRing 1.4s ease-out ${i*0.45}s infinite`,
          top:'50%', left:'50%', transform:'translate(-50%,-50%)', pointerEvents:'none'
        }} />
      ))}

      <div style={{...R.robot, animation:state==='idle'?'robotFloat 4s ease-in-out infinite':'none', filter:`drop-shadow(0 0 16px ${c.glow})`}}>
        <div style={R.antennaBase}>
          <div style={{...R.antennaDot, background:c.core, animation:'antennaPulse 1.5s ease-in-out infinite'}} />
        </div>

        <div style={R.head}>
          <div style={R.eyeRow}>
            <div style={{...R.eye, background:c.eye, animation:state==='listening'?'eyePulse 0.6s ease-in-out infinite':'eyePulse 2.5s ease-in-out infinite'}} />
            <div style={{...R.eye, background:c.eye, animation:state==='listening'?'eyePulse 0.6s ease-in-out infinite 0.1s':'eyePulse 2.5s ease-in-out infinite 0.3s'}} />
          </div>
          <div style={R.mouth}>
            {state === 'speaking' ? [0,1,2,3,4].map(i => (
              <div key={i} style={{width:3, background:c.core, borderRadius:2, animation:`speakBar 0.4s ease-in-out ${i*0.08}s infinite`}} />
            )) : <div style={{width:24, height:2, background:c.core, borderRadius:2, opacity:0.6}} />}
          </div>
        </div>

        <div style={R.neck} />
        <div style={R.body}>
          <div style={R.reactorWrap}>
            <div style={{...R.reactorRing, borderColor:c.core, animation:'coreRotate 3s linear infinite'}} />
            <div style={{...R.reactorCore, background:`radial-gradient(circle, #fff 0%, ${c.core} 50%, transparent 75%)`}} />
          </div>
        </div>

        <div style={{...R.arm, left:-18}}><div style={{...R.armJoint, background:c.core}} /></div>
        <div style={{...R.arm, right:-18}}><div style={{...R.armJoint, background:c.core}} /></div>

        <div style={R.legRow}>
          <div style={R.leg}><div style={{...R.foot, background:c.core}} /></div>
          <div style={R.leg}><div style={{...R.foot, background:c.core}} /></div>
        </div>
      </div>

      <div style={{...R.stateLabel, color:c.core}}>
        {state === 'idle' && '● STANDBY'}
        {state === 'listening' && '◉ LISTENING...'}
        {state === 'thinking' && '◌ THINKING...'}
        {state === 'speaking' && '▶ SPEAKING...'}
      </div>
    </div>
  )
}

const R = {
  wrap: {position:'relative', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', width:160, flexShrink:0, userSelect:'none', cursor:'pointer'},
  robot: {display:'flex', flexDirection:'column', alignItems:'center', position:'relative'},
  antennaBase: {width:2, height:18, background:'rgba(0,255,200,0.3)', marginBottom:0, position:'relative', display:'flex', justifyContent:'center'},
  antennaDot: {width:8, height:8, borderRadius:'50%', position:'absolute', top:-4},
  head: {width:64, height:48, background:'linear-gradient(135deg, #001a14 0%, #002a20 100%)', border:'1.5px solid rgba(0,255,200,0.4)', borderRadius:10, position:'relative', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:6},
  eyeRow: {display:'flex', gap:14},
  eye: {width:10, height:10, borderRadius:'50%', boxShadow:'0 0 8px currentColor'},
  mouth: {display:'flex', alignItems:'flex-end', gap:2, height:20, justifyContent:'center'},
  neck: {width:12, height:6, background:'rgba(0,255,200,0.2)', borderLeft:'1px solid rgba(0,255,200,0.3)', borderRight:'1px solid rgba(0,255,200,0.3)'},
  body: {width:80, height:80, background:'linear-gradient(135deg, #001a14 0%, #002a20 100%)', border:'1.5px solid rgba(0,255,200,0.35)', borderRadius:12, position:'relative', display:'flex', alignItems:'center', justifyContent:'center'},
  reactorWrap: {width:32, height:32, position:'relative', display:'flex', alignItems:'center', justifyContent:'center'},
  reactorRing: {position:'absolute', inset:0, borderRadius:'50%', border:'2px solid', borderTopColor:'transparent'},
  reactorCore: {width:14, height:14, borderRadius:'50%'},
  arm: {position:'absolute', top:10, width:12, height:56, background:'rgba(0,30,22,0.8)', border:'1px solid rgba(0,255,200,0.2)', borderRadius:6, display:'flex', justifyContent:'center', alignItems:'flex-end', paddingBottom:4},
  armJoint: {width:8, height:8, borderRadius:'50%'},
  legRow: {display:'flex', gap:8, marginTop:4},
  leg: {width:16, height:28, background:'rgba(0,30,22,0.8)', border:'1px solid rgba(0,255,200,0.2)', borderRadius:6, display:'flex', justifyContent:'center', alignItems:'flex-end', paddingBottom:3},
  foot: {width:20, height:6, borderRadius:3},
  stateLabel: {marginTop:10, fontFamily:'Orbitron', fontSize:8, letterSpacing:2, opacity:0.8},
}

// ─── Voice Hook ──────────────────────────────────────────────
function useVoice(onResult, onError) {
  const recogRef = useRef(null)
  const [supported] = useState(() => 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window)

  const start = useCallback((lang = 'bn-BD') => {
    if (!supported) {
      onError?.('Voice recognition not supported')
      return false
    }

    try {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition
      const rec = new SR()

      rec.lang = lang
      rec.interimResults = true
      rec.maxAlternatives = 1
      rec.continuous = false

      let finalTranscript = ''

      rec.onresult = (e) => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const transcript = e.results[i][0].transcript
          if (e.results[i].isFinal) {
            finalTranscript += transcript
          }
        }
      }

      rec.onend = () => {
        if (finalTranscript.trim()) {
          onResult(finalTranscript.trim())
        } else {
          onError?.('No speech detected')
        }
      }

      rec.onerror = (e) => {
        if (e.error !== 'aborted') {
          onError?.(e.error === 'no-speech' ? 'No speech detected' : 
                    e.error === 'audio-capture' ? 'No microphone found' :
                    e.error === 'not-allowed' ? 'Microphone permission denied' :
                    e.error === 'network' ? 'Network error' : `Error: ${e.error}`)
        }
      }

      rec.start()
      recogRef.current = rec
      return true
    } catch (err) {
      onError?.('Failed to start voice')
      return false
    }
  }, [supported, onResult, onError])

  const stop = useCallback(() => {
    recogRef.current?.stop()
    recogRef.current = null
  }, [])

  return { supported, start, stop }
}

// ─── TTS Hook ──────────────────────────────────────────────
function useTTS() {
  const [supported] = useState(() => 'speechSynthesis' in window)

  const speak = useCallback((text, lang = 'bn-BD') => {
    if (!supported) return false
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.volume = 1.0

    const voices = window.speechSynthesis.getVoices()
    const voice = voices.find(v => v.lang.includes(lang === 'bn-BD' ? 'bn' : 'en'))
    if (voice) utterance.voice = voice

    window.speechSynthesis.speak(utterance)
    return true
  }, [supported])

  const stop = useCallback(() => {
    window.speechSynthesis.cancel()
  }, [])

  return { supported, speak, stop }
}

// ─── Main ChatPanel ──────────────────────────────────────────
export default function ChatPanel() {
  const { messages, addMessage, isProcessing, setProcessing, userName } = useAtlasStore()
  const [input, setInput] = useState('')
  const [robotState, setRobotState] = useState('idle')
  const [isListening, setIsListening] = useState(false)
  const [voiceLang, setVoiceLang] = useState('bn-BD')
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    if (isListening) setRobotState('listening')
    else if (isProcessing) setRobotState('thinking')
    else setRobotState('idle')
  }, [isListening, isProcessing])

  const { speak, stop: stopTTS } = useTTS()

  const send = async (text) => {
    const t = (text || input).trim()
    if (!t || isProcessing) return

    setInput('')
    addMessage('user', t)
    setProcessing(true)
    setRobotState('thinking')

    try {
      const res = await sendCommand(t)

      if (res.response) {
        addMessage('assistant', res.response)

        if (res.intent && res.intent !== 'chat' && res.intent !== 'unknown') {
          addMessage('system', `Agent: ${res.intent} | ${Math.round((res.confidence||0)*100)}% | ${res.method||'unknown'}`)
        }

        setRobotState('speaking')
        speak(res.response, res.language === 'bn' ? 'bn-BD' : 'en-US')
        setTimeout(() => setRobotState('idle'), Math.min(3000 + res.response.length*50, 8000))
      }
    } catch {
      addMessage('assistant', '❌ Server unreachable. Backend চলছে তো?')
      setRobotState('idle')
    } finally {
      setProcessing(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const handleVoiceError = useCallback((errorMsg) => {
    setIsListening(false)
    addMessage('assistant', `⚠️ ${errorMsg}`)
    setRobotState('idle')
  }, [addMessage])

  const handleVoiceResult = useCallback((transcript) => {
    setIsListening(false)
    if (transcript.trim()) {
      send(transcript)
    }
  }, [send])

  const { supported: voiceSupported, start: startVoice, stop: stopVoice } = useVoice(handleVoiceResult, handleVoiceError)

  const handleRobotClick = () => {
    if (isProcessing) return

    if (isListening) {
      stopVoice()
      setIsListening(false)
      stopTTS()
    } else {
      if (!voiceSupported) {
        addMessage('assistant', '⚠️ Voice recognition শুধু Chrome-এ কাজ করে।')
        return
      }
      stopTTS()
      const started = startVoice(voiceLang)
      if (started) setIsListening(true)
    }
  }

  const quickCommands = [
    { text: 'open youtube', label: '▶️ YouTube' },
    { text: 'optimize pc', label: '⚡ Optimize' },
    { text: 'organize downloads', label: '📁 Organize' },
    { text: 'research AI', label: '🔍 Research' },
    { text: 'pomodoro 25', label: '⏱️ Focus' },
    { text: 'lock pc', label: '🔒 Lock' },
  ]

  return (
    <div style={S.panel}>
      <div style={S.top}>
        {/* Robot */}
        <div style={S.robotCol}>
          <AtlasRobot state={robotState} onClick={handleRobotClick} />

          <div style={S.robotHint}>
            {isListening ? '◉ Listening...' : 'Robot-এ ক্লিক করে Voice চালু করুন'}
          </div>

          <button onClick={() => setVoiceLang(l => l==='bn-BD'?'en-US':'bn-BD')} style={S.langToggle}>
            {voiceLang === 'bn-BD' ? '🇧🇩 BN' : '🇺🇸 EN'}
          </button>

          <div style={S.quickCommands}>
            {quickCommands.map((cmd, i) => (
              <button key={i} onClick={() => send(cmd.text)} disabled={isProcessing} style={S.quickBtn}>
                {cmd.label}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div style={S.messages}>
          {messages.length === 0 && (
            <div style={S.empty}>
              <p style={S.emptyTitle}>ATLAS 7.0</p>
              <p style={S.emptyText}>optimize pc, organize downloads, open youtube...</p>
              <div style={S.agentList}>
                {['⚡ PC','📁 File','🌐 Web','🎵 Media','✅ Productivity','🔒 Security','📱 App','💻 Terminal'].map((tag,i) => (
                  <span key={i} style={S.agentTag}>{tag}</span>
                ))}
              </div>
            </div>
          )}

          <AnimatePresence>
            {messages.map(msg => (
              <motion.div 
                key={msg.id} 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                style={{
                  ...S.bubble,
                  alignSelf: msg.role === 'user' ? 'flex-end' : msg.role === 'system' ? 'center' : 'flex-start',
                  background: msg.role === 'user' ? 'rgba(0,255,200,0.1)' : msg.role === 'system' ? 'rgba(255,100,0,0.1)' : 'rgba(0,20,40,0.85)',
                  borderColor: msg.role === 'user' ? 'rgba(0,255,200,0.4)' : msg.role === 'system' ? 'rgba(255,100,0,0.3)' : 'rgba(0,150,255,0.3)',
                  maxWidth: msg.role === 'system' ? '90%' : '82%',
                }}
              >
                <div style={S.bubbleRole}>
                  {msg.role === 'user' ? `👤 ${userName}` : msg.role === 'system' ? '🔧 System' : '🤖 Atlas'}
                  <span style={{fontSize:9, opacity:0.5}}>{msg.time}</span>
                </div>
                <pre style={S.bubbleText}>{msg.text}</pre>
              </motion.div>
            ))}
          </AnimatePresence>

          {isProcessing && (
            <motion.div style={{...S.bubble, alignSelf:'flex-start', background:'rgba(20,0,40,0.9)', borderColor:'#8833ff'}}>
              <span style={{color:'#aa66ff'}}>◌ Agent Processing...</span>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div style={S.inputRow}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="যেমন: optimize pc, organize downloads, open youtube, research ai..."
          rows={2}
          style={S.input}
          disabled={isListening}
        />
        <button 
          onClick={handleRobotClick}
          style={{...S.voiceBtn, background:isListening?'rgba(255,100,0,0.3)':'rgba(0,255,200,0.1)', borderColor:isListening?'#ff6600':'var(--cyan-border)'}}
        >
          {isListening ? '⏹️' : '🎤'}
        </button>
        <motion.button 
          whileHover={{ scale: 1.05 }} 
          whileTap={{ scale: 0.95 }} 
          onClick={() => send()}
          disabled={isProcessing || !input.trim() || isListening}
          style={{...S.sendBtn, opacity: isProcessing || !input.trim() || isListening ? 0.4 : 1}}
        >
          ▶
        </motion.button>
      </div>
    </div>
  )
}

const S = {
  panel: {display:'flex', flexDirection:'column', height:'100%', gap:8, background:'var(--bg-dark)'},
  top: {flex:1, display:'flex', gap:16, overflow:'hidden', minHeight:0},
  robotCol: {display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'flex-start', gap:8, padding:'10px', flexShrink:0, width:170},
  robotHint: {fontSize:10, color:'var(--text-dim)', textAlign:'center', maxWidth:160, minHeight:28},
  langToggle: {padding:'4px 10px', borderRadius:12, border:'1px solid var(--cyan-border)', background:'rgba(0,255,200,0.1)', color:'var(--cyan)', fontSize:11, cursor:'pointer', fontFamily:'Orbitron'},
  quickCommands: {display:'flex', flexDirection:'column', gap:4, width:'100%', marginTop:8},
  quickBtn: {display:'flex', alignItems:'center', gap:6, padding:'5px 8px', borderRadius:6, border:'1px solid rgba(0,255,200,0.2)', background:'rgba(0,255,200,0.05)', color:'var(--cyan)', fontSize:11, cursor:'pointer', fontFamily:'Rajdhani', transition:'all 0.2s'},
  messages: {flex:1, overflowY:'auto', display:'flex', flexDirection:'column', gap:10, padding:'4px 4px 8px'},
  empty: {flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:12, opacity:0.7},
  emptyTitle: {fontFamily:'Orbitron', fontSize:15, color:'var(--cyan)', letterSpacing:3},
  emptyText: {fontSize:12, color:'var(--text-dim)', textAlign:'center'},
  agentList: {display:'flex', flexWrap:'wrap', gap:6, justifyContent:'center', maxWidth:300},
  agentTag: {padding:'2px 8px', borderRadius:10, border:'1px solid rgba(0,255,200,0.2)', background:'rgba(0,255,200,0.05)', color:'var(--cyan)', fontSize:10, fontFamily:'Rajdhani'},
  bubble: {padding:'10px 14px', borderRadius:10, border:'1px solid', backdropFilter:'blur(10px)'},
  bubbleRole: {fontSize:10, color:'var(--text-dim)', marginBottom:5, display:'flex', justifyContent:'space-between', fontFamily:'Orbitron'},
  bubbleText: {fontSize:13.5, color:'#e0f0e8', lineHeight:1.6, whiteSpace:'pre-wrap', fontFamily:'Rajdhani'},
  inputRow: {display:'flex', gap:8, padding:'0 2px 2px'},
  input: {flex:1, background:'rgba(0,255,200,0.04)', border:'1px solid var(--cyan-border)', borderRadius:8, padding:'10px 14px', color:'var(--cyan)', fontFamily:'Rajdhani', fontSize:14, resize:'none', outline:'none'},
  voiceBtn: {width:40, borderRadius:8, border:'1px solid', fontSize:16, cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--cyan)'},
  sendBtn: {width:48, background:'rgba(0,255,200,0.15)', border:'1px solid var(--cyan-border)', borderRadius:8, color:'var(--cyan)', fontSize:18, cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center'},
}