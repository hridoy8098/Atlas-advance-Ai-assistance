// voice.js — reply playback for the browser and the phone app.
//
// The server renders replies with Edge TTS (MP3), which gives reliable Bengali
// and English voices on every platform. The Android WebView has no usable
// speechSynthesis voices, so <audio> is the primary path there too. If a
// desktop browser blocks autoplay or the TTS request fails, we fall back to the
// built-in speechSynthesis voice instead of staying silent.
import { fetchSpeech } from './api'

let audioEl = null
let objectUrl = null
let pendingResolve = null
let utterance = null
let playbackCycle = 0

const settle = value => {
  const resolve = pendingResolve
  pendingResolve = null
  if (resolve) resolve(value)
}

const stopAudio = () => {
  if (audioEl) {
    try {
      audioEl.pause()
    } catch {}
    audioEl.onended = null
    audioEl.onerror = null
    audioEl = null
  }
  if (objectUrl) {
    try {
      URL.revokeObjectURL(objectUrl)
    } catch {}
    objectUrl = null
  }
}

const stopSpeech = () => {
  if (!utterance) return
  const synth = window.speechSynthesis
  try {
    synth?.cancel()
  } catch {}
  utterance.onend = null
  utterance.onerror = null
  utterance = null
}

export const stopPlayback = () => {
  // Invalidate any in-flight TTS fetch so it cannot start playing after stop.
  playbackCycle += 1
  stopSpeech()
  stopAudio()
  settle(false)
}

const browserLanguage = (text, language) => {
  const hint = String(language || '').toLowerCase()
  if (hint.startsWith('bn')) return 'bn-BD'
  if (hint.startsWith('en')) return 'en-US'
  return /[\u0980-\u09ff]/.test(text) ? 'bn-BD' : 'en-US'
}

/**
 * Speak a reply through the server's Edge TTS voice. Returns null only when
 * there is nothing to say; every other case returns a stoppable playback.
 */
export const speakReply = (text, language = 'auto') => {
  const clean = String(text || '').trim()
  if (!clean) return null

  stopPlayback()
  const cycle = ++playbackCycle
  let cancelled = false
  let fellBack = false

  const isCurrent = () => !cancelled && cycle === playbackCycle

  const finish = value => {
    if (!isCurrent()) return
    stopSpeech()
    stopAudio()
    settle(value)
  }

  const speakLocally = () => {
    if (!isCurrent() || fellBack) return
    fellBack = true

    const synth = window.speechSynthesis
    if (!synth || typeof SpeechSynthesisUtterance === 'undefined') {
      finish(false)
      return
    }

    stopAudio()

    const lang = browserLanguage(clean, language)
    const line = new SpeechSynthesisUtterance(clean.slice(0, 600))
    line.lang = lang
    line.rate = 1.02

    const voices = synth.getVoices?.() || []
    const voice =
      voices.find(v => v.lang === lang) ||
      voices.find(v => String(v.lang || '').toLowerCase().startsWith(lang.slice(0, 2)))
    if (voice) line.voice = voice

    utterance = line
    line.onend = () => {
      if (utterance === line) utterance = null
      settle(true)
    }
    line.onerror = () => {
      if (utterance === line) utterance = null
      settle(false)
    }

    try {
      synth.speak(line)
    } catch {
      utterance = null
      finish(false)
    }
  }

  const promise = new Promise(resolve => {
    pendingResolve = resolve
  })

  fetchSpeech(clean.slice(0, 1200), language)
    .then(response => {
      if (!isCurrent()) return false
      const blob = response?.data instanceof Blob ? response.data : new Blob([response?.data])
      if (!blob.size) throw new Error('Empty speech response')

      objectUrl = URL.createObjectURL(blob)
      audioEl = new Audio(objectUrl)
      audioEl.preload = 'auto'
      audioEl.setAttribute('playsinline', '')

      audioEl.onended = () => finish(true)
      audioEl.onerror = () => {
        if (isCurrent()) {
          stopAudio()
          speakLocally()
        }
      }

      return audioEl.play().catch(() => {
        // Autoplay blocked or playback unavailable: use the browser voice.
        speakLocally()
      })
    })
    .catch(() => speakLocally())

  return {
    promise,
    stop: () => {
      cancelled = true
      if (cycle !== playbackCycle) return
      stopPlayback()
    },
  }
}
