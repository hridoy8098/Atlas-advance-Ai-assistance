// HUDCenter.jsx — Expressive Robot + Chat
import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useAtlasStore from '../../store/useAtlasStore'
import { sendCommand, getVoiceSpeaking, stopSpeech } from '../../services/api'
import AtlasRobot from './AtlasRobot'

// ── Emotion picker: response dekhe robot er mood ঠিক করে ──
function pickEmotion(res) {
  const text = String(res?.response || '')
  const intent = String(res?.intent || '').toLowerCase()

  if (/❌|\berror\b|failed|could ?n[o']t|unreachable|offline/i.test(text)) return 'error'
  if (/✅|\bdone\b|success|complete|finished|হয়ে গেছে|সম্পন্ন/i.test(text)) return 'happy'

  if (/lock|shutdown|sleep|security/i.test(intent)) return 'alert'
  if (/research|study|search|news|weather|wikipedia/i.test(intent)) return 'curious'
  if (/optimize|clean|file|organize|terminal|command|pc/i.test(intent)) return 'focused'
  if (/media|youtube|music|play|video/i.test(intent)) return 'happy'

  return 'neutral'
}

// ── Voice hook ──
function useVoice(onResult) {
  const recogRef = useRef(null)
  const supported = typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)

  const start = useCallback(() => {
    if (!supported) return false
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SR()
    rec.lang = 'bn-BD'
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.onresult = (e) => { onResult(e.results[0][0].transcript) }
    rec.onerror = () => { onResult(null) }
    rec.onend = () => {}
    rec.start()
    recogRef.current = rec
    return true
  }, [supported, onResult])

  const stop = useCallback(() => { recogRef.current?.stop() }, [])
  return { supported, start, stop }
}

// ── Main ──
export default function HUDCenter() {
  const { messages, addMessage, isProcessing, setProcessing, userName } = useAtlasStore()
  const [robotEmotion, setRobotEmotion] = useState('neutral')
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Speaking-sync bookkeeping
  const cycleRef = useRef(0)
  const pollTimer = useRef(null)
  const emoResetTimer = useRef(null)
  const hardTimer = useRef(null)

  // State priority: listening > thinking > speaking > idle
  const robotState = isListening ? 'listening' : isProcessing ? 'thinking' : isSpeaking ? 'speaking' : 'idle'

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  // Boot greeting — robot wakes up happy
  useEffect(() => {
    setRobotEmotion('happy')
    const t = setTimeout(() => setRobotEmotion('neutral'), 2600)
    return () => clearTimeout(t)
  }, [])

  // Timer cleanup on unmount
  useEffect(() => () => {
    clearTimeout(pollTimer.current)
    clearTimeout(emoResetTimer.current)
    clearTimeout(hardTimer.current)
  }, [])

  const stopSpeaking = useCallback(() => {
    cycleRef.current++
    clearTimeout(pollTimer.current)
    clearTimeout(emoResetTimer.current)
    clearTimeout(hardTimer.current)
    setIsSpeaking(false)
    setRobotEmotion('neutral')
    stopSpeech().catch(() => {})
  }, [])

  // Esc = stop voice
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && isSpeaking) stopSpeaking() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isSpeaking, stopSpeaking])

  // ── Speaking sync: backend TTS এর সাথে robot er মুখ মিলিয়ে চালায় ──
  const beginSpeaking = useCallback((text) => {
    const cycle = ++cycleRef.current
    clearTimeout(pollTimer.current)
    clearTimeout(emoResetTimer.current)
    clearTimeout(hardTimer.current)

    const startedAt = Date.now()
    const estMs = Math.min(1600 + text.length * 55, 16000)
    let sawSpeaking = false

    setIsSpeaking(true)

    const finish = () => {
      if (cycle !== cycleRef.current) return
      setIsSpeaking(false)
      emoResetTimer.current = setTimeout(() => {
        if (cycle === cycleRef.current) setRobotEmotion('neutral')
      }, 1500)
    }

    // Hard safety net — eta er beshi chola uchit na
    hardTimer.current = setTimeout(finish, estMs * 2 + 6000)

    const tick = async () => {
      if (cycle !== cycleRef.current) return
      const elapsed = Date.now() - startedAt
      if (elapsed > estMs * 2 + 5000) return finish()

      let speaking = null
      try { speaking = (await getVoiceSpeaking()).speaking } catch { speaking = null }
      if (cycle !== cycleRef.current) return

      const minShown = elapsed > 1100
      if (speaking === true) sawSpeaking = true
      if (speaking === false && sawSpeaking && minShown) return finish()
      if (speaking === false && !sawSpeaking && elapsed >= estMs && minShown) return finish()
      if (speaking === null && elapsed >= estMs && minShown) return finish()

      pollTimer.current = setTimeout(tick, 320)
    }
    tick()
  }, [])

  const send = async (text) => {
    const t = (text || input).trim()
    if (!t || isProcessing) return
    setInput('')
    addMessage('user', t)
    setProcessing(true)
    try {
      const res = await sendCommand(t)
      if (res.response) {
        addMessage('assistant', res.response)
        setRobotEmotion(pickEmotion(res))
        beginSpeaking(String(res.response))
      }
    } catch {
      addMessage('assistant', '❌ Server unreachable. Backend চলছে কিনা দেখো।')
      setRobotEmotion('error')
      setTimeout(() => setRobotEmotion('neutral'), 2600)
    } finally {
      setProcessing(false)
    }
  }

  const { supported: voiceOk, start: startV, stop: stopV } = useVoice((transcript) => {
    setIsListening(false)
    if (transcript) send(transcript)
  })

  const handleRobotClick = () => {
    if (isProcessing) return
    if (isListening) { stopV(); setIsListening(false) }
    else {
      if (isSpeaking) stopSpeaking() // echo এড়াতে আগে speech বন্ধ
      if (!voiceOk) { addMessage('assistant', '⚠️ Chrome browser এ voice কাজ করে।'); return }
      if (startV()) setIsListening(true)
    }
  }

  return (
    <div style={S.center}>
      {/* HUD decorative rings */}
      <div style={S.hudRing1} />
      <div style={S.hudRing2} />

      {/* Top: Robot */}
      <div style={S.robotArea}>
        <AtlasRobot state={robotState} emotion={robotEmotion} onClick={handleRobotClick} />
        {isSpeaking && (
          <button onClick={stopSpeaking} style={S.stopBtn} title="Stop voice (Esc)">
            ◼ STOP VOICE
          </button>
        )}
      </div>

      {/* Bottom: Messages + Input */}
      <div style={S.chatArea}>
        <div style={S.messages}>
          {messages.length === 0 && (
            <div style={S.empty}>
              <span style={S.emptyIcon}>⬡</span>
              <span style={S.emptyText}>ATLAS READY — Robot এ click করো বা নিচে type করো</span>
            </div>
          )}
          <AnimatePresence>
            {messages.map(msg => (
              <motion.div key={msg.id} initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.2 }}
                style={{
                  ...S.bubble,
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  background: msg.role === 'user' ? 'rgba(0,255,200,0.07)' : 'rgba(0,20,50,0.8)',
                  borderColor: msg.role === 'user' ? 'rgba(0,255,200,0.3)' : 'rgba(0,120,255,0.25)',
                }}>
                <div style={S.bubbleHeader}>
                  <span style={{ fontFamily:'Orbitron,monospace', fontSize:9, letterSpacing:1 }}>
                    {msg.role === 'user' ? '▸ ' + userName.toUpperCase() : '▸ ATLAS'}
                  </span>
                  <span style={{ fontSize:9, opacity:0.35 }}>{msg.time}</span>
                </div>
                <pre style={S.bubbleText}>{msg.text}</pre>
              </motion.div>
            ))}
          </AnimatePresence>

          {isProcessing && (
            <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }}
              style={{ ...S.bubble, alignSelf:'flex-start', borderColor:'rgba(153,51,255,0.3)', background:'rgba(20,0,40,0.8)' }}>
              <div style={{ display:'flex', gap:5, alignItems:'center' }}>
                <style>{`@keyframes dotB{0%,100%{transform:translateY(0);opacity:.4}50%{transform:translateY(-5px);opacity:1}}`}</style>
                {[0,1,2].map(i => <div key={i} style={{ width:6, height:6, borderRadius:'50%', background:'#9933ff', animation:`dotB 1s ease-in-out ${i*0.2}s infinite` }} />)}
                <span style={{ fontFamily:'Orbitron,monospace', fontSize:9, color:'#aa66ff', letterSpacing:2, marginLeft:4 }}>PROCESSING</span>
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        <div style={S.inputRow}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Command দাও... (Enter to send)"
            rows={2}
            style={S.input}
          />
          <motion.button whileHover={{ scale:1.05 }} whileTap={{ scale:0.95 }}
            onClick={() => send()}
            disabled={isProcessing || !input.trim()}
            style={{ ...S.sendBtn, opacity: isProcessing || !input.trim() ? 0.3 : 1 }}>▶</motion.button>
        </div>
      </div>
    </div>
  )
}

const S = {
  center: { display:'flex', flexDirection:'column', position:'relative', overflow:'hidden' },
  hudRing1: { position:'absolute', width:320, height:320, borderRadius:'50%', border:'1px solid rgba(0,255,200,0.06)', top:'30%', left:'50%', transform:'translate(-50%,-50%)', pointerEvents:'none' },
  hudRing2: { position:'absolute', width:240, height:240, borderRadius:'50%', border:'1px solid rgba(0,255,200,0.04)', top:'30%', left:'50%', transform:'translate(-50%,-50%)', pointerEvents:'none' },
  robotArea: { display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', paddingTop:12, flexShrink:0 },
  stopBtn: { marginTop:4, padding:'3px 12px', borderRadius:12, border:'1px solid rgba(0,170,255,0.4)', background:'rgba(0,170,255,0.12)', color:'#33ccff', fontFamily:'Orbitron,monospace', fontSize:9, letterSpacing:1.5, cursor:'pointer' },
  chatArea: { flex:1, display:'flex', flexDirection:'column', gap:6, overflow:'hidden', padding:'8px 6px 4px' },
  messages: { flex:1, overflowY:'auto', display:'flex', flexDirection:'column', gap:7, paddingRight:4 },
  empty: { display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:8, flex:1, opacity:0.4, paddingTop:20 },
  emptyIcon: { fontSize:30, color:'#00ffc8' },
  emptyText: { fontSize:10, color:'rgba(0,255,200,0.6)', fontFamily:'Orbitron,monospace', letterSpacing:2, textAlign:'center' },
  bubble: { maxWidth:'85%', padding:'8px 12px', borderRadius:8, border:'1px solid' },
  bubbleHeader: { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:4, color:'rgba(0,255,200,0.45)' },
  bubbleText: { fontSize:12, color:'#d0eee0', lineHeight:1.65, whiteSpace:'pre-wrap', fontFamily:'Rajdhani,sans-serif', margin:0 },
  inputRow: { display:'flex', gap:6, flexShrink:0 },
  input: { flex:1, background:'rgba(0,255,200,0.04)', border:'1px solid rgba(0,255,200,0.2)', borderRadius:6, padding:'8px 12px', color:'#00ffc8', fontFamily:'Share Tech Mono,monospace', fontSize:12, resize:'none', outline:'none', lineHeight:1.5 },
  sendBtn: { width:44, background:'rgba(0,255,200,0.1)', border:'1px solid rgba(0,255,200,0.25)', borderRadius:6, color:'#00ffc8', fontSize:16, cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 },
}
