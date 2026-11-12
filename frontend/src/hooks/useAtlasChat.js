// useAtlasChat.js — chat send/receive plus TTS state synchronisation.
import { useCallback, useEffect, useRef } from 'react'
import useAtlasStore from '../store/useAtlasStore'
import { sendCommand, getVoiceSpeaking } from '../services/api'
import { speakReply, stopPlayback, unlockAudio } from '../services/voice'
import { runNativeAction } from '../services/native'

export default function useAtlasChat({ onStateChange, onPlaybackFailed } = {}) {
  const messages = useAtlasStore(s => s.messages)
  const isProcessing = useAtlasStore(s => s.isProcessing)
  const addMessage = useAtlasStore(s => s.addMessage)
  const clearMessages = useAtlasStore(s => s.clearMessages)
  const setProcessing = useAtlasStore(s => s.setProcessing)
  const incrementCommandCount = useAtlasStore(s => s.incrementCommandCount)

  const pollRef = useRef(null)
  const hardRef = useRef(null)
  const cycleRef = useRef(0)
  const processingRef = useRef(false)

  const clearTimers = useCallback(() => {
    clearTimeout(pollRef.current)
    clearTimeout(hardRef.current)
    pollRef.current = null
    hardRef.current = null
  }, [])

  useEffect(
    () => () => {
      cycleRef.current += 1
      clearTimers()
    },
    [clearTimers]
  )

  const beginSpeaking = useCallback(
    (text, language = 'auto') => {
      // A replay click is a user gesture; this also keeps the context warm for
      // replies that arrive after the mic/send activation has expired.
      unlockAudio()
      const cycle = ++cycleRef.current
      clearTimers()

      const startedAt = Date.now()
      const estMs = Math.min(1600 + String(text).length * 55, 16000)
      let sawSpeaking = false

      onStateChange?.('speaking')

      const finish = () => {
        if (cycle !== cycleRef.current) return
        clearTimers()
        onStateChange?.('idle')
      }

      // The browser/phone has the speaker, the cloud server does not: the
      // client asks for an Edge TTS MP3 and ends "speaking" when audio stops.
      const playback = speakReply(text, language)
      if (playback) {
        hardRef.current = setTimeout(finish, 60000)
        playback.promise
          .then(ok => {
            if (cycle !== cycleRef.current) return
            finish()
            if (!ok) onPlaybackFailed?.()
          })
          .catch(() => {
            if (cycle !== cycleRef.current) return
            finish()
            onPlaybackFailed?.()
          })
        return
      }

      hardRef.current = setTimeout(finish, estMs * 2 + 6000)

      const tick = async () => {
        if (cycle !== cycleRef.current) return
        const elapsed = Date.now() - startedAt
        if (elapsed > estMs * 2 + 5000) return finish()

        let speaking = null
        try {
          speaking = (await getVoiceSpeaking())?.speaking ?? null
        } catch {
          speaking = null
        }
        if (cycle !== cycleRef.current) return

        if (speaking === true) sawSpeaking = true
        if (speaking === false && sawSpeaking && elapsed > 900) return finish()
        if (speaking === false && !sawSpeaking && elapsed >= estMs) return finish()
        if (speaking === null && elapsed >= estMs) return finish()

        pollRef.current = setTimeout(tick, 350)
      }

      tick()
    },
    [clearTimers, onPlaybackFailed, onStateChange]
  )

  const send = useCallback(
    async raw => {
      const text = String(raw ?? '').trim()
      if (!text || processingRef.current) return

      // Runs inside the send click/keypress, before the async AI request.
      unlockAudio()

      processingRef.current = true
      addMessage('user', text)
      incrementCommandCount()
      setProcessing(true)
      onStateChange?.('thinking')

      try {
        const res = await sendCommand(text)
        const nativeRes = await runNativeAction(res)
        const finalres = nativeRes || res
        if (finalres?.response || finalres?.message) {
          const reply = String(finalres.message || finalres.response)
          addMessage('assistant', reply)
          setProcessing(false)
          beginSpeaking(reply, finalres.language || 'auto')
        } else {
          setProcessing(false)
          onStateChange?.('idle')
        }
      } catch {
        addMessage('assistant', '❌ Server unreachable. Backend চলছে কিনা দেখো।')
        setProcessing(false)
        onStateChange?.('idle')
      } finally {
        processingRef.current = false
      }
    },
    [addMessage, beginSpeaking, incrementCommandCount, onStateChange, setProcessing]
  )

  const speak = useCallback(
    (text, language = 'auto') => beginSpeaking(text, language),
    [beginSpeaking]
  )

  const clear = useCallback(() => {
    clearTimers()
    cycleRef.current += 1
    stopPlayback()
    clearMessages()
    onStateChange?.('idle')
  }, [clearMessages, clearTimers, onStateChange])

  return { messages, isProcessing, send, speak, clear }
}
