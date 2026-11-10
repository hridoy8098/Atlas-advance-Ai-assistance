// useMicrophone.js — record on the phone and let the server transcribe it.
//
// Android WebView does not implement the Web Speech API, and the cloud box has
// no microphone, so the client records a clip with MediaRecorder and uploads it
// to /api/voice/transcribe (Groq Whisper). Recording stops automatically after
// a short silence, so a single tap is enough.
import { useCallback, useEffect, useRef, useState } from 'react'
import { transcribeAudio } from '../services/api'

const MAX_RECORD_MS = 12000
const SILENCE_MS = 1400
const SPEECH_RMS = 0.02
const MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']

const pickMime = () => {
  if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return ''
  return MIME_CANDIDATES.find(type => MediaRecorder.isTypeSupported(type)) || ''
}

export default function useMicrophone({ language = 'auto', onText, onError } = {}) {
  const [supported] = useState(
    () =>
      typeof navigator !== 'undefined' &&
      Boolean(navigator.mediaDevices?.getUserMedia) &&
      typeof MediaRecorder !== 'undefined'
  )
  const [listening, setListening] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const sessionRef = useRef(null)
  const mountedRef = useRef(true)

  const release = useCallback(session => {
    clearTimeout(session.timer)
    if (session.raf) cancelAnimationFrame(session.raf)
    try {
      session.stream?.getTracks().forEach(track => track.stop())
    } catch {}
    try {
      session.audioContext?.close()
    } catch {}
  }, [])

  const stopSession = useCallback(
    async (session, upload) => {
      if (!session || session.stopped) return
      session.stopped = true

      const blob = await new Promise(resolve => {
        if (session.recorder.state === 'inactive') {
          resolve(null)
          return
        }
        session.recorder.onstop = () =>
          resolve(new Blob(session.chunks, { type: session.mimeType || 'audio/webm' }))
        try {
          session.recorder.stop()
        } catch {
          resolve(null)
        }
      })

      release(session)
      if (sessionRef.current === session) sessionRef.current = null
      if (mountedRef.current) setListening(false)

      // A tap that produced almost nothing is not worth a network round trip.
      if (!upload || !blob || blob.size < 1200) return

      if (mountedRef.current) setTranscribing(true)
      try {
        const res = await transcribeAudio(blob, language)
        if (!mountedRef.current) return
        if (res?.success && res.text) onText?.(res.text)
        else onError?.(res?.error || 'Kichu bujhte parlam na. Abar try koro.')
      } catch {
        if (mountedRef.current) onError?.('Voice upload failed. Connection check koro.')
      } finally {
        if (mountedRef.current) setTranscribing(false)
      }
    },
    [language, onError, onText, release]
  )

  const cancel = useCallback(() => {
    const session = sessionRef.current
    if (!session) return
    sessionRef.current = null
    session.stopped = true
    release(session)
    try {
      if (session.recorder.state !== 'inactive') session.recorder.stop()
    } catch {}
    if (mountedRef.current) setListening(false)
  }, [release])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      const session = sessionRef.current
      if (session) {
        sessionRef.current = null
        session.stopped = true
        release(session)
        try {
          if (session.recorder.state !== 'inactive') session.recorder.stop()
        } catch {}
      }
    }
  }, [release])

  const start = useCallback(async () => {
    if (sessionRef.current) return true
    if (!supported) {
      onError?.('Ei device-e microphone recording supported na.')
      return false
    }

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      })
    } catch (err) {
      onError?.(
        err?.name === 'NotAllowedError' || err?.name === 'SecurityError'
          ? 'Microphone permission denied. Phone Settings → Apps → Atlas 7 → Permissions → Microphone.'
          : 'Microphone পাওয়া যায়নি।'
      )
      return false
    }

    let recorder
    const mimeType = pickMime()
    try {
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    } catch {
      try {
        recorder = new MediaRecorder(stream)
      } catch {
        stream.getTracks().forEach(track => track.stop())
        onError?.('Recording start korte parlam na.')
        return false
      }
    }

    const session = {
      recorder,
      stream,
      chunks: [],
      mimeType: recorder.mimeType || mimeType,
      stopped: false,
    }
    recorder.ondataavailable = event => {
      if (event.data?.size) session.chunks.push(event.data)
    }
    recorder.start(250)

    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (AudioCtx) {
      const audioContext = new AudioCtx()
      session.audioContext = audioContext
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 1024
      audioContext.createMediaStreamSource(stream).connect(analyser)

      const buffer = new Uint8Array(analyser.fftSize)
      const startedAt = performance.now()
      let spoke = false
      let quietSince = 0

      const tick = () => {
        if (session.stopped) return
        analyser.getByteTimeDomainData(buffer)
        let sum = 0
        for (let i = 0; i < buffer.length; i++) {
          const value = (buffer[i] - 128) / 128
          sum += value * value
        }
        const rms = Math.sqrt(sum / buffer.length)
        const now = performance.now()

        if (rms > SPEECH_RMS) {
          spoke = true
          quietSince = 0
        } else if (spoke) {
          if (!quietSince) quietSince = now
          else if (now - quietSince > SILENCE_MS) {
            stopSession(session, true)
            return
          }
        }

        if (now - startedAt > MAX_RECORD_MS) {
          stopSession(session, true)
          return
        }
        session.raf = requestAnimationFrame(tick)
      }
      tick()
    } else {
      session.timer = setTimeout(() => stopSession(session, true), MAX_RECORD_MS)
    }

    sessionRef.current = session
    if (mountedRef.current) setListening(true)
    return true
  }, [onError, stopSession, supported])

  const stop = useCallback(async () => {
    const session = sessionRef.current
    if (!session) return
    await stopSession(session, true)
  }, [stopSession])

  return { supported, listening, transcribing, start, stop, cancel }
}
