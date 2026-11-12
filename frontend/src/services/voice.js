// voice.js — reply playback for the browser and the phone app.
//
// Replies arrive as Edge TTS MP3. On the web we play them through an
// AudioContext that was unlocked by the mic/send tap, because a reply can take
// longer than the browser's ~5-second autoplay window. HTMLAudio and
// speechSynthesis remain fallbacks for older browsers and blocked contexts.
import { fetchSpeech, isNativeApp } from './api'

let audioEl = null
let objectUrl = null
let pendingResolve = null
let utterance = null
let speechGuard = null
let audioContext = null
let bufferSource = null
let bufferResolve = null
let audioUnlocked = false
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

const stopBuffer = () => {
  const source = bufferSource
  const resolve = bufferResolve
  bufferSource = null
  bufferResolve = null
  if (source) {
    try {
      source.onended = null
      source.stop()
    } catch {}
    try {
      source.disconnect()
    } catch {}
  }
  if (resolve) resolve(false)
}

const stopSpeech = () => {
  if (speechGuard) {
    clearTimeout(speechGuard)
    speechGuard = null
  }
  if (!utterance) return
  const synth = window.speechSynthesis
  try {
    synth?.cancel()
  } catch {}
  utterance.onstart = null
  utterance.onend = null
  utterance.onerror = null
  utterance = null
}

const getAudioContext = () => {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) return null
  if (!audioContext || audioContext.state === 'closed') {
    try {
      audioContext = new Ctx()
      audioUnlocked = false
    } catch {
      return null
    }
  }
  return audioContext
}

/**
 * Call synchronously from a mic/play/send tap. The silent blip plus resume()
 * unlocks Web Audio for replies that arrive seconds later.
 */
export const unlockAudio = () => {
  if (isNativeApp()) return false
  const ctx = getAudioContext()
  if (!ctx) return false
  try {
    if (ctx.state === 'suspended') ctx.resume().catch(() => {})
    if (!audioUnlocked) {
      const source = ctx.createBufferSource()
      source.buffer = ctx.createBuffer(1, 1, 22050)
      source.connect(ctx.destination)
      source.start(0)
      audioUnlocked = true
    }
  } catch {}
  return true
}

export const stopPlayback = () => {
  // Invalidate any in-flight TTS fetch so it cannot start playing after stop.
  playbackCycle += 1
  stopSpeech()
  stopBuffer()
  stopAudio()
  settle(false)
}

const browserLanguage = (text, language) => {
  const hint = String(language || '').toLowerCase()
  if (hint.startsWith('bn')) return 'bn-BD'
  if (hint.startsWith('en')) return 'en-US'
  return /[\u0980-\u09ff]/.test(text) ? 'bn-BD' : 'en-US'
}

const playWithWebAudio = async (blob, isCurrent) => {
  const ctx = getAudioContext()
  if (!ctx) return false

  try {
    if (ctx.state === 'suspended') await ctx.resume()
    if (ctx.state !== 'running') return false

    const data = await blob.arrayBuffer()
    if (!isCurrent()) return false
    const buffer = await ctx.decodeAudioData(data)
    if (!isCurrent()) return false

    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    bufferSource = source

    return await new Promise(resolve => {
      bufferResolve = resolve
      source.onended = () => {
        if (bufferSource === source) bufferSource = null
        bufferResolve = null
        resolve(true)
      }
      try {
        source.start(0)
      } catch {
        if (bufferSource === source) bufferSource = null
        bufferResolve = null
        resolve(false)
      }
    })
  } catch {
    return false
  }
}

/**
 * Speak a reply through the server's Edge TTS voice. Returns null only when
 * there is nothing to say; every other case returns a stoppable playback.
 */
export const speakReply = (text, language = 'auto') => {
  const clean = String(text || '').trim()
  if (!clean) return null

  if (!isNativeApp()) unlockAudio()
  stopPlayback()
  const cycle = ++playbackCycle
  let cancelled = false
  let fellBack = false

  const isCurrent = () => !cancelled && cycle === playbackCycle

  const finish = value => {
    if (!isCurrent()) return
    stopSpeech()
    stopBuffer()
    stopAudio()
    settle(value)
  }

  const speakLocally = () => {
    if (!isCurrent() || fellBack) return
    fellBack = true

    // Android WebView exposes speechSynthesis but has no voices; resolving
    // false is better than waiting for an utterance that never ends.
    if (isNativeApp()) {
      finish(false)
      return
    }

    const synth = window.speechSynthesis
    if (!synth || typeof SpeechSynthesisUtterance === 'undefined') {
      finish(false)
      return
    }

    stopBuffer()
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
    let started = false

    // Some browsers accept speak() but never emit an event when no matching
    // voice exists. Resolve quickly so the UI can offer the replay button.
    speechGuard = setTimeout(() => {
      speechGuard = null
      if (!started && utterance === line) {
        stopSpeech()
        settle(false)
      }
    }, 3500)

    line.onstart = () => {
      started = true
      if (speechGuard) {
        clearTimeout(speechGuard)
        speechGuard = null
      }
    }
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
      stopSpeech()
      finish(false)
    }
  }

  const promise = new Promise(resolve => {
    pendingResolve = resolve
  })

  fetchSpeech(clean.slice(0, 1200), language)
    .then(async response => {
      if (!isCurrent()) return false
      const blob = response?.data instanceof Blob ? response.data : new Blob([response?.data])
      if (!blob.size) throw new Error('Empty speech response')

      // Web: an unlocked AudioContext never waits for fresh user activation.
      if (!isNativeApp()) {
        const played = await playWithWebAudio(blob, isCurrent)
        if (!isCurrent()) return false
        if (played) {
          finish(true)
          return true
        }
      }

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
