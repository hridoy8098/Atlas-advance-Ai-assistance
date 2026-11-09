import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Music, Video, Image, Wrench, Play, Pause, Square } from 'lucide-react'
import {
  getMediaLibrary, getMediaStatus, playMedia, pauseMedia, resumeMedia, stopMedia,
  generateMeme, removeBackground, createPodcast, generateSubtitles, downloadVideo, generateImage,
} from '../../services/api'

export default function MediaPanel() {
  const [activeTab, setActiveTab] = useState('music')
  const [note, setNote] = useState('')

  // Music
  const [tracks, setTracks] = useState([])
  const [player, setPlayer] = useState({ playing: false, paused: false, track: null })
  const [loadingLib, setLoadingLib] = useState(false)

  // Video download
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [audioOnly, setAudioOnly] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [dlResult, setDlResult] = useState(null)

  // Image generation
  const [prompt, setPrompt] = useState('')
  const [size, setSize] = useState('1024x1024')
  const [generating, setGenerating] = useState(false)
  const [imageResult, setImageResult] = useState(null)

  // Tools
  const [toolImage, setToolImage] = useState('')
  const [memeTop, setMemeTop] = useState('')
  const [memeBottom, setMemeBottom] = useState('')
  const [memeResult, setMemeResult] = useState(null)
  const [bgResult, setBgResult] = useState(null)
  const [podScript, setPodScript] = useState('')
  const [podVoice, setPodVoice] = useState('')
  const [podResult, setPodResult] = useState(null)
  const [subPath, setSubPath] = useState('')
  const [subResult, setSubResult] = useState(null)
  const [busy, setBusy] = useState('')

  const loadMusic = async () => {
    setLoadingLib(true)
    try {
      const [libRes, statusRes] = await Promise.allSettled([getMediaLibrary(), getMediaStatus()])
      if (libRes.status === 'fulfilled' && libRes.value?.success) setTracks(libRes.value.tracks || [])
      if (statusRes.status === 'fulfilled' && statusRes.value?.success) setPlayer(statusRes.value)
    } catch (e) {
      setNote(e.message)
    }
    setLoadingLib(false)
  }

  useEffect(() => { loadMusic() }, [])

  const refreshStatus = async () => {
    try {
      const res = await getMediaStatus()
      if (res?.success) setPlayer(res)
    } catch { /* status is best-effort */ }
  }

  const doPlay = async (track) => {
    try {
      const res = await playMedia(track.path)
      setNote(res?.success ? `Playing ${track.name}` : (res?.error || 'Playback failed'))
      refreshStatus()
    } catch (e) { setNote(e.message) }
  }

  const doPause = async () => {
    try {
      const res = player.paused ? await resumeMedia() : await pauseMedia()
      setNote(res?.success ? (player.paused ? 'Resumed' : 'Paused') : (res?.error || 'Failed'))
      refreshStatus()
    } catch (e) { setNote(e.message) }
  }

  const doStop = async () => {
    try {
      const res = await stopMedia()
      setNote(res?.success ? 'Stopped' : (res?.error || 'Failed'))
      refreshStatus()
    } catch (e) { setNote(e.message) }
  }

  const doDownload = async () => {
    if (!youtubeUrl.trim()) return
    setDownloading(true)
    setDlResult(null)
    try {
      const res = await downloadVideo(youtubeUrl.trim(), audioOnly)
      setDlResult(res)
      if (res?.success) { setNote(`Saved ${res.title || 'video'}`); loadMusic() }
      else setNote(res?.error || 'Download failed')
    } catch (e) { setNote(e.message) }
    setDownloading(false)
  }

  const doGenerate = async () => {
    if (!prompt.trim()) return
    setGenerating(true)
    setImageResult(null)
    try {
      const res = await generateImage(prompt.trim(), size)
      setImageResult(res)
      setNote(res?.success ? 'Image generated' : (res?.error || 'Generation failed'))
    } catch (e) { setNote(e.message) }
    setGenerating(false)
  }

  const doMeme = async () => {
    if (!toolImage.trim()) { setNote('Image path required'); return }
    setBusy('meme')
    try {
      const res = await generateMeme(toolImage.trim(), memeTop, memeBottom)
      setMemeResult(res)
      setNote(res?.success ? 'Meme created' : (res?.error || 'Meme failed'))
    } catch (e) { setNote(e.message) }
    setBusy('')
  }

  const doRemoveBg = async () => {
    if (!toolImage.trim()) { setNote('Image path required'); return }
    setBusy('bg')
    try {
      const res = await removeBackground(toolImage.trim())
      setBgResult(res)
      setNote(res?.success ? 'Background removed' : (res?.error || 'Remove BG failed'))
    } catch (e) { setNote(e.message) }
    setBusy('')
  }

  const doPodcast = async () => {
    if (!podScript.trim()) { setNote('Script required'); return }
    setBusy('pod')
    try {
      const res = await createPodcast(podScript.trim(), podVoice.trim() || undefined)
      setPodResult(res)
      setNote(res?.success ? `Podcast saved (${res.size_kb} KB)` : (res?.error || 'Podcast failed'))
    } catch (e) { setNote(e.message) }
    setBusy('')
  }

  const doSubtitles = async () => {
    if (!subPath.trim()) { setNote('Audio/video path required'); return }
    setBusy('sub')
    try {
      const res = await generateSubtitles(subPath.trim())
      setSubResult(res)
      setNote(res?.success ? `Subtitle saved (${res.lines} lines)` : (res?.error || 'Subtitle failed'))
    } catch (e) { setNote(e.message) }
    setBusy('')
  }

  const tabs = [
    { id: 'music', label: 'MUSIC', icon: Music },
    { id: 'video', label: 'DOWNLOAD', icon: Video },
    { id: 'images', label: 'IMAGE GEN', icon: Image },
    { id: 'tools', label: 'TOOLS', icon: Wrench },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto auto 1fr', gap: 10, height: '100%' }}>
      <div style={{ display: 'flex', gap: 6 }}>
        {tabs.map(tab => (
          <motion.button key={tab.id} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...S.tab,
              background: activeTab === tab.id ? 'rgba(0,255,200,0.1)' : 'transparent',
              borderColor: activeTab === tab.id ? 'rgba(0,255,200,0.4)' : 'rgba(0,255,200,0.12)',
              color: activeTab === tab.id ? 'var(--cyan)' : 'var(--text-dim)',
            }}>
            <tab.icon size={14} />
            <span style={{ fontSize: 10, letterSpacing: 1 }}>{tab.label}</span>
          </motion.button>
        ))}
      </div>

      {note && <div style={{ fontSize: 10, color: 'rgba(0,255,200,0.7)' }}>{note}</div>}

      <AnimatePresence mode="wait">
        {activeTab === 'music' && (
          <motion.div key="music" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 10 }}>
                NOW PLAYING
              </div>
              <div style={{ textAlign: 'center', marginBottom: 12 }}>
                <div style={{ fontSize: 32, marginBottom: 6 }}>🎵</div>
                <div style={{ fontFamily: 'Orbitron', fontSize: 12, color: 'var(--cyan)', letterSpacing: 1 }}>
                  {player.track || 'Nothing playing'}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
                  {player.playing ? (player.paused ? 'PAUSED' : 'PLAYING') : 'STOPPED'}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16 }}>
                <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }} onClick={doPause}
                  style={{ ...S.playBtn, borderColor: player.paused ? '#ffaa00' : 'var(--cyan)', color: player.paused ? '#ffaa00' : 'var(--cyan)' }}>
                  {player.paused ? <Play size={20} /> : <Pause size={20} />}
                </motion.button>
                <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }} onClick={doStop}
                  style={S.ctrlBtn}><Square size={16} /></motion.button>
              </div>
            </div>

            <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {loadingLib && <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>Scanning library…</div>}
              {!loadingLib && tracks.length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--text-dim)', textAlign: 'center', marginTop: 12 }}>
                  No audio files found. Add music to ~/Music or Downloads/media/music.
                </div>
              )}
              {tracks.map((track, i) => (
                <motion.div key={track.path || i} whileHover={{ x: 3 }}
                  onClick={() => doPlay(track)}
                  style={{
                    ...S.trackItem,
                    background: player.track === track.name ? 'rgba(0,255,200,0.08)' : 'transparent',
                    borderLeft: player.track === track.name ? '2px solid #00ffc8' : '2px solid transparent',
                  }}>
                  <span style={{ fontSize: 16 }}>🎵</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, color: 'var(--cyan)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{track.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{track.path}</div>
                  </div>
                  <Play size={12} color="var(--text-dim)" />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === 'video' && (
          <motion.div key="video" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 12 }}>YOUTUBE DOWNLOADER</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={youtubeUrl} onChange={e => setYoutubeUrl(e.target.value)}
                  placeholder="Paste YouTube URL..." style={S.input} />
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                  onClick={doDownload} disabled={!youtubeUrl.trim() || downloading}
                  style={{ ...S.smallBtn, opacity: (!youtubeUrl.trim() || downloading) ? 0.4 : 1 }}>
                  {downloading ? 'WORKING' : 'FETCH'}
                </motion.button>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, fontSize: 11, color: 'var(--text-dim)', cursor: 'pointer' }}>
                <input type="checkbox" checked={audioOnly} onChange={e => setAudioOnly(e.target.checked)} />
                Audio only (m4a)
              </label>
            </div>
            <div style={{ ...S.card, flex: 1, overflow: 'auto' }}>
              {!dlResult && (
                <div style={{ textAlign: 'center', color: 'var(--text-dim)', paddingTop: 24 }}>
                  <Video size={32} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
                  <div style={{ fontSize: 12 }}>Downloads go to Downloads/media</div>
                </div>
              )}
              {dlResult && !dlResult.success && (
                <div style={{ fontSize: 11, color: '#ff6666' }}>{dlResult.error}</div>
              )}
              {dlResult?.success && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontFamily: 'Orbitron', fontSize: 11, color: 'var(--cyan)' }}>{dlResult.title}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-dim)', wordBreak: 'break-all' }}>{dlResult.path}</div>
                  {dlResult.duration && <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{Math.round(dlResult.duration / 60)} min</div>}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === 'images' && (
          <motion.div key="images" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 12 }}>AI IMAGE GENERATION</div>
              <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Describe the image…"
                rows={3} style={{ ...S.input, flex: 'unset', width: '100%', resize: 'vertical', boxSizing: 'border-box' }} />
              <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
                <select value={size} onChange={e => setSize(e.target.value)} style={S.select}>
                  {['1024x1024', '1280x720', '720x1280'].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                  onClick={doGenerate} disabled={!prompt.trim() || generating}
                  style={{ ...S.smallBtn, marginLeft: 'auto', opacity: (!prompt.trim() || generating) ? 0.4 : 1 }}>
                  {generating ? 'GENERATING…' : 'GENERATE'}
                </motion.button>
              </div>
            </div>
            {imageResult && (
              <div style={S.card}>
                {imageResult.success ? (
                  <>
                    <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: '#00ff88', marginBottom: 6 }}>SAVED · {imageResult.size}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', wordBreak: 'break-all' }}>{imageResult.path}</div>
                  </>
                ) : (
                  <div style={{ fontSize: 11, color: '#ff6666' }}>{imageResult.error}</div>
                )}
              </div>
            )}
          </motion.div>
        )}

        {activeTab === 'tools' && (
          <motion.div key="tools" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%', overflow: 'auto' }}>
            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>SOURCE IMAGE</div>
              <input value={toolImage} onChange={e => setToolImage(e.target.value)} placeholder="Full path to an image file" style={{ ...S.input, width: '100%', boxSizing: 'border-box' }} />
            </div>

            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>MEME GENERATOR</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input value={memeTop} onChange={e => setMemeTop(e.target.value)} placeholder="Top text" style={S.input} />
                <input value={memeBottom} onChange={e => setMemeBottom(e.target.value)} placeholder="Bottom text" style={S.input} />
                <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} onClick={doMeme}
                  disabled={busy === 'meme'} style={S.smallBtn}>{busy === 'meme' ? '…' : 'MAKE'}</motion.button>
              </div>
              {memeResult && (
                <div style={{ fontSize: 10, marginTop: 6, color: memeResult.success ? 'var(--text-dim)' : '#ff6666', wordBreak: 'break-all' }}>
                  {memeResult.success ? memeResult.output : memeResult.error}
                </div>
              )}
            </div>

            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>BACKGROUND REMOVER</div>
              <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={doRemoveBg}
                disabled={busy === 'bg'} style={S.smallBtn}>{busy === 'bg' ? 'WORKING…' : 'REMOVE BACKGROUND'}</motion.button>
              {bgResult && (
                <div style={{ fontSize: 10, marginTop: 6, color: bgResult.success ? 'var(--text-dim)' : '#ff6666', wordBreak: 'break-all' }}>
                  {bgResult.success ? `${bgResult.output} (${bgResult.removed_pixels} px removed)` : bgResult.error}
                </div>
              )}
            </div>

            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>PODCAST CREATOR</div>
              <textarea value={podScript} onChange={e => setPodScript(e.target.value)} placeholder="Script…" rows={3}
                style={{ ...S.input, flex: 'unset', width: '100%', resize: 'vertical', boxSizing: 'border-box' }} />
              <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                <input value={podVoice} onChange={e => setPodVoice(e.target.value)} placeholder="Voice (optional, e.g. bn-BD-NabanitaNeural)" style={S.input} />
                <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} onClick={doPodcast}
                  disabled={busy === 'pod'} style={S.smallBtn}>{busy === 'pod' ? '…' : 'CREATE'}</motion.button>
              </div>
              {podResult && (
                <div style={{ fontSize: 10, marginTop: 6, color: podResult.success ? 'var(--text-dim)' : '#ff6666', wordBreak: 'break-all' }}>
                  {podResult.success ? `${podResult.path} · ${podResult.size_kb} KB` : podResult.error}
                </div>
              )}
            </div>

            <div style={S.card}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>SUBTITLE GENERATOR</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input value={subPath} onChange={e => setSubPath(e.target.value)} placeholder="Path to audio/video file" style={S.input} />
                <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} onClick={doSubtitles}
                  disabled={busy === 'sub'} style={S.smallBtn}>{busy === 'sub' ? '…' : 'GENERATE'}</motion.button>
              </div>
              {subResult && (
                <div style={{ fontSize: 10, marginTop: 6, color: subResult.success ? 'var(--text-dim)' : '#ff6666', wordBreak: 'break-all' }}>
                  {subResult.success ? `${subResult.srt_path} · ${subResult.lines} lines` : subResult.error}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const S = {
  tab: { display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid', cursor: 'pointer', fontFamily: 'Rajdhani', fontSize: 12, background: 'transparent' },
  card: { background: 'rgba(0,20,16,0.7)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 10, padding: 14 },
  ctrlBtn: { width: 36, height: 36, borderRadius: '50%', border: '1px solid rgba(0,255,200,0.2)', background: 'rgba(0,255,200,0.05)', color: 'var(--cyan)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  playBtn: { width: 52, height: 52, borderRadius: '50%', border: '2px solid', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  trackItem: { display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 6, cursor: 'pointer' },
  input: { flex: 1, minWidth: 0, background: 'rgba(0,255,200,0.04)', border: '1px solid rgba(0,255,200,0.2)', borderRadius: 6, padding: '8px 12px', color: 'var(--cyan)', fontSize: 12, outline: 'none', fontFamily: 'Rajdhani' },
  select: { background: 'rgba(0,255,200,0.04)', border: '1px solid rgba(0,255,200,0.2)', borderRadius: 6, padding: '7px 10px', color: 'var(--cyan)', fontSize: 12, outline: 'none', fontFamily: 'Rajdhani' },
  smallBtn: { padding: '8px 16px', borderRadius: 6, border: '1px solid rgba(0,255,200,0.3)', background: 'rgba(0,255,200,0.08)', color: 'var(--cyan)', fontFamily: 'Rajdhani', fontSize: 12, cursor: 'pointer' },
}
