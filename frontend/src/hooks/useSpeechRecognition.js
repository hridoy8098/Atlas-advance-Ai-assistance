// useSpeechRecognition.js — browser speech-to-text wrapper.
import { useCallback, useRef, useState } from 'react'

const ERROR_TEXT = {
  'no-speech': 'No speech detected',
  'audio-capture': 'No microphone found',
  'not-allowed': 'Microphone permission denied',
  network: 'Speech recognition network error',
}

export default function useSpeechRecognition({ lang = 'bn-BD', onResult, onError, onEnd } = {}) {
  const recRef = useRef(null)
  const [supported] = useState(
    () => typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)
  )

  const stop = useCallback(() => {
    try {
      recRef.current?.stop()
    } catch {}
    recRef.current = null
  }, [])

  const start = useCallback(() => {
    if (!supported) {
      onError?.('Voice recognition ei browser-e supported na. Chrome use koro.')
      return false
    }
    if (recRef.current) {
      try {
        recRef.current.abort()
      } catch {}
      recRef.current = null
    }

    try {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition
      const rec = new SR()
      rec.lang = lang
      rec.interimResults = false
      rec.maxAlternatives = 1
      rec.continuous = false

      rec.onresult = event => {
        const transcript = event.results?.[0]?.[0]?.transcript || ''
        recRef.current = null
        if (transcript.trim()) onResult?.(transcript.trim())
      }

      rec.onerror = event => {
        recRef.current = null
        if (event.error !== 'aborted') {
          onError?.(ERROR_TEXT[event.error] || `Voice error: ${event.error}`)
        }
      }

      rec.onend = () => {
        recRef.current = null
        onEnd?.()
      }

      rec.start()
      recRef.current = rec
      return true
    } catch {
      recRef.current = null
      onError?.('Voice recognition start korte parlam na.')
      return false
    }
  }, [lang, onError, onEnd, onResult, supported])

  return { supported, start, stop }
}
