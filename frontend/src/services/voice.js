// voice.js — speech playback for the phone app.
//
// Android WebView ships no usable speechSynthesis voices, so replies are
// rendered by the server with Edge TTS (MP3) and played through <audio>.
// Desktop browsers keep the old behaviour: the laptop server speaks locally.
import { fetchSpeech, isNativeApp } from './api'

let audioEl = null
let objectUrl = null
let pendingResolve = null

const releaseAudio = () => {
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

export const stopPlayback = () => {
  const resolve = pendingResolve
  pendingResolve = null
  releaseAudio()
  if (resolve) resolve(false)
}

/**
 * Speak a reply on the phone. Returns null when the client should stay silent
 * (desktop, where the server already speaks through the laptop speakers).
 */
export const speakReply = (text, language = 'auto') => {
  const clean = String(text || '').trim()
  if (!clean || !isNativeApp()) return null

  stopPlayback()
  let cancelled = false

  const promise = fetchSpeech(clean.slice(0, 1200), language)
    .then(response => {
      if (cancelled) return false
      const blob = response?.data instanceof Blob ? response.data : new Blob([response?.data])
      if (!blob.size) return false

      objectUrl = URL.createObjectURL(blob)
      audioEl = new Audio(objectUrl)
      audioEl.preload = 'auto'
      audioEl.setAttribute('playsinline', '')

      return new Promise(resolve => {
        pendingResolve = resolve
        audioEl.onended = () => {
          pendingResolve = null
          resolve(true)
        }
        audioEl.onerror = () => {
          pendingResolve = null
          resolve(false)
        }
        audioEl.play().catch(() => {
          pendingResolve = null
          resolve(false)
        })
      })
    })
    .catch(() => false)
    .finally(() => {
      if (cancelled) return
      releaseAudio()
    })

  return {
    promise,
    stop: () => {
      cancelled = true
      stopPlayback()
    },
  }
}
