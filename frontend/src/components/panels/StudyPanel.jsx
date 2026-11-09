import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Timer, Notebook, FileText, Sparkles } from 'lucide-react'
import {
  getFlashcards, addFlashcard, reviewCard, getDueCards, getStudyStats,
  logStudySession, getStudyPlan,
} from '../../services/api'

const pomodoros = [
  { label: 'FOCUS', duration: 25, color: '#00ffc8' },
  { label: 'BREAK', duration: 5, color: '#00aaff' },
]

export default function StudyPanel() {
  const [activeTab, setActiveTab] = useState('pomodoro')
  const [flipIndex, setFlipIndex] = useState(null)
  const [currentCard, setCurrentCard] = useState(0)

  const [cards, setCards] = useState([])
  const [stats, setStats] = useState(null)
  const [dueIds, setDueIds] = useState([])
  const [newQ, setNewQ] = useState('')
  const [newA, setNewA] = useState('')
  const [studyNote, setStudyNote] = useState('')
  const [loadingCards, setLoadingCards] = useState(false)

  const [planSubject, setPlanSubject] = useState('Physics')
  const [planHours, setPlanHours] = useState(2)
  const [plan, setPlan] = useState(null)

  const loadStudy = async () => {
    setLoadingCards(true)
    try {
      const [listRes, statsRes, dueRes] = await Promise.all([
        getFlashcards(), getStudyStats(), getDueCards(50),
      ])
      if (listRes?.success) setCards(listRes.cards || [])
      if (statsRes?.success) setStats(statsRes)
      if (dueRes?.success) setDueIds((dueRes.cards || []).map(c => c.id))
    } catch (e) {
      setStudyNote(e.message)
    }
    setLoadingCards(false)
  }

  useEffect(() => { loadStudy() }, [])

  // Pomodoro
  const [pomoRunning, setPomoRunning] = useState(false)
  const [pomoMode, setPomoMode] = useState(0)
  const [secondsLeft, setSecondsLeft] = useState(pomodoros[0].duration * 60)
  const pomoRef = useRef(null)

  useEffect(() => {
    if (pomoRunning) {
      pomoRef.current = setInterval(() => {
        setSecondsLeft(s => {
          if (s <= 1) {
            clearInterval(pomoRef.current)
            setPomoRunning(false)
            return 0
          }
          return s - 1
        })
      }, 1000)
    }
    return () => clearInterval(pomoRef.current)
  }, [pomoRunning])

  const startPomo = () => {
    if (secondsLeft === 0) {
      setSecondsLeft(pomodoros[pomoMode].duration * 60)
    }
    setPomoRunning(true)
  }

  const resetPomo = () => {
    clearInterval(pomoRef.current)
    setPomoRunning(false)
    setSecondsLeft(pomodoros[pomoMode].duration * 60)
  }

  const switchPomoMode = (idx) => {
    clearInterval(pomoRef.current)
    setPomoRunning(false)
    setPomoMode(idx)
    setSecondsLeft(pomodoros[idx].duration * 60)
  }

  const logPomodoro = async () => {
    try {
      const res = await logStudySession('Study', pomodoros[pomoMode].duration)
      setStudyNote(res?.success ? `Logged ${res.minutes}m · today ${res.today_minutes}m` : (res?.error || 'Log failed'))
      loadStudy()
    } catch (e) {
      setStudyNote(e.message)
    }
  }

  const createCard = async () => {
    if (!newQ.trim() || !newA.trim()) { setStudyNote('Question and answer required'); return }
    try {
      const res = await addFlashcard(newQ.trim(), newA.trim(), 'default')
      if (res?.success) {
        setNewQ('')
        setNewA('')
        setStudyNote('Card added')
        loadStudy()
      } else setStudyNote(res?.error || 'Add failed')
    } catch (e) {
      setStudyNote(e.message)
    }
  }

  const rateCard = async (cardId, quality) => {
    try {
      const res = await reviewCard(cardId, quality)
      setStudyNote(res?.success ? `Next review in ${res.interval_days} day(s)` : (res?.error || 'Review failed'))
      loadStudy()
    } catch (e) {
      setStudyNote(e.message)
    }
  }

  const makePlan = async () => {
    try {
      const res = await getStudyPlan(planSubject, null, planHours)
      if (res?.success) setPlan(res)
      else setStudyNote(res?.error || 'Plan failed')
    } catch (e) {
      setStudyNote(e.message)
    }
  }

  const current = cards[currentCard]

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  const tabs = [
    { id: 'pomodoro', label: 'POMODORO', icon: Timer },
    { id: 'flashcards', label: 'FLASHCARDS', icon: BookOpen },
    { id: 'notes', label: 'STATS', icon: Notebook },
    { id: 'papers', label: 'EXAM PLAN', icon: FileText },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12, height: '100%' }}>
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

      {studyNote && <div style={{ fontSize: 10, color: 'rgba(0,255,200,0.7)' }}>{studyNote}</div>}

      <AnimatePresence mode="wait">
        {activeTab === 'pomodoro' && (
          <motion.div key="pomodoro" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, height: '100%' }}>
            <div style={{ display: 'flex', gap: 8 }}>
              {pomodoros.map((p, i) => (
                <motion.button key={p.label} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                  onClick={() => switchPomoMode(i)}
                  style={{
                    ...S.modeBtn,
                    background: pomoMode === i ? `${p.color}22` : 'transparent',
                    borderColor: pomoMode === i ? p.color : 'rgba(0,255,200,0.15)',
                    color: pomoMode === i ? p.color : 'var(--text-dim)',
                  }}>
                  {p.label} · {p.duration}m
                </motion.button>
              ))}
            </div>

            <div style={{ position: 'relative', width: 180, height: 180 }}>
              <svg width="180" height="180" style={{ transform: 'rotate(-90deg)' }}>
                <circle cx="90" cy="90" r="78" fill="none" stroke="rgba(0,255,200,0.1)" strokeWidth="6" />
                <motion.circle cx="90" cy="90" r="78" fill="none"
                  stroke={pomodoros[pomoMode].color} strokeWidth="6" strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 78}
                  strokeDashoffset={2 * Math.PI * 78 * (1 - secondsLeft / (pomodoros[pomoMode].duration * 60))}
                  style={{ transition: 'stroke-dashoffset 1s linear' }} />
              </svg>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ fontFamily: 'Share Tech Mono', fontSize: 38, color: pomodoros[pomoMode].color }}>{formatTime(secondsLeft)}</div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginTop: 4 }}>{pomodoros[pomoMode].label}</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              {!pomoRunning ? (
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                  onClick={startPomo} style={S.pomoBtn}>
                  {secondsLeft === 0 ? 'RESTART' : 'START'}
                </motion.button>
              ) : (
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                  onClick={() => setPomoRunning(false)} style={{ ...S.pomoBtn, background: 'rgba(255,50,50,0.15)', borderColor: 'rgba(255,50,50,0.4)', color: '#ff6666' }}>
                  PAUSE
                </motion.button>
              )}
              <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                onClick={resetPomo} style={{ ...S.pomoBtn, background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(0,255,200,0.15)', color: 'var(--text-dim)' }}>
                RESET
              </motion.button>
              <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                onClick={logPomodoro} style={{ ...S.pomoBtn, background: 'rgba(0,170,255,0.1)', borderColor: 'rgba(0,170,255,0.35)', color: '#00aaff' }}>
                LOG
              </motion.button>
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
              {stats ? `${stats.due_today} due · ${stats.reviewed_today} reviewed today` : 'Loading study stats…'}
            </div>
          </motion.div>
        )}

        {activeTab === 'flashcards' && (
          <motion.div key="flashcards" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, height: '100%', overflow: 'auto' }}>
            {loadingCards && <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>Loading…</div>}
            {!current && !loadingCards && (
              <div style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', marginTop: 24 }}>
                No flashcards yet — add your first one below.
              </div>
            )}

            {current && (
              <>
                <div style={{ position: 'relative', width: '100%', maxWidth: 420, height: 180, perspective: 1000 }}
                  onClick={() => setFlipIndex(flipIndex === current.id ? null : current.id)}>
                  <motion.div
                    animate={{ rotateY: flipIndex === current.id ? 180 : 0 }}
                    transition={{ duration: 0.5 }}
                    style={{ width: '100%', height: '100%', transformStyle: 'preserve-3d', cursor: 'pointer', position: 'relative' }}>
                    <div style={{ ...S.cardFace, backfaceVisibility: 'hidden', background: 'rgba(0,25,20,0.85)', border: '1px solid rgba(0,255,200,0.25)' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 12 }}>QUESTION</div>
                      <div style={{ fontFamily: 'Orbitron', fontSize: 14, color: 'var(--cyan)', lineHeight: 1.5, textAlign: 'center' }}>{current.question}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 12, letterSpacing: 1 }}>Click to reveal</div>
                    </div>
                    <div style={{ ...S.cardFace, backfaceVisibility: 'hidden', transform: 'rotateY(180deg)', background: 'rgba(10,0,30,0.9)', border: '1px solid rgba(150,50,255,0.3)' }}>
                      <div style={{ fontSize: 10, color: '#aa66ff', letterSpacing: 2, marginBottom: 12 }}>ANSWER</div>
                      <div style={{ fontSize: 14, color: '#cc88ff', lineHeight: 1.6, textAlign: 'center' }}>{current.answer}</div>
                    </div>
                  </motion.div>
                </div>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    onClick={() => { setFlipIndex(null); setCurrentCard(i => (i - 1 + cards.length) % cards.length) }}
                    style={S.cardNav}>◀ PREV</motion.button>
                  <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{currentCard + 1} / {cards.length}</span>
                  <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    onClick={() => { setFlipIndex(null); setCurrentCard(i => (i + 1) % cards.length) }}
                    style={S.cardNav}>NEXT ▶</motion.button>
                </div>

                {dueIds.includes(current.id) && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    {[{ q: 1, label: 'AGAIN' }, { q: 3, label: 'HARD' }, { q: 4, label: 'GOOD' }, { q: 5, label: 'EASY' }].map(b => (
                      <motion.button key={b.q} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                        onClick={() => rateCard(current.id, b.q)} style={S.cardNav}>{b.label}</motion.button>
                    ))}
                  </div>
                )}
              </>
            )}

            <div style={{ display: 'flex', gap: 6, width: '100%', maxWidth: 460, marginTop: 4 }}>
              <input value={newQ} onChange={e => setNewQ(e.target.value)} placeholder="Question" style={S.input} />
              <input value={newA} onChange={e => setNewA(e.target.value)} placeholder="Answer" style={S.input} />
              <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} onClick={createCard} style={S.smallBtn}>ADD</motion.button>
            </div>
          </motion.div>
        )}

        {activeTab === 'notes' && (
          <motion.div key="notes" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10, height: '100%', overflow: 'auto' }}>
            {[
              { title: 'TOTAL CARDS', key: 'total_cards', color: '#00ffc8' },
              { title: 'DUE TODAY', key: 'due_today', color: '#ffaa00' },
              { title: 'REVIEWED TODAY', key: 'reviewed_today', color: '#00aaff' },
              { title: 'AVG EASE', key: 'avg_ease', color: '#ff88ff' },
            ].map((n, i) => (
              <div key={i} style={S.card}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <Sparkles size={14} color={n.color} />
                  <span style={{ fontFamily: 'Orbitron', fontSize: 10, color: n.color, letterSpacing: 1 }}>{n.title}</span>
                </div>
                <div style={{ fontFamily: 'Share Tech Mono', fontSize: 24, color: n.color }}>
                  {stats ? (stats[n.key] ?? 0) : '—'}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
                  {stats ? `Updated ${stats.checked_at || 'just now'}` : 'Loading…'}
                </div>
              </div>
            ))}
            <div style={{ ...S.card, gridColumn: 'span 2', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                {stats ? `SM-2 spaced repetition · ease ${stats.avg_ease ?? 2.5}` : 'Spaced repetition (SM-2)'}
              </div>
              <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={loadStudy} style={S.smallBtn}>REFRESH</motion.button>
            </div>
          </motion.div>
        )}

        {activeTab === 'papers' && (
          <motion.div key="papers" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%', overflow: 'auto' }}>
            <div style={{ ...S.card, display: 'flex', gap: 6, alignItems: 'center' }}>
              <input value={planSubject} onChange={e => setPlanSubject(e.target.value)} placeholder="Subject" style={S.input} />
              <input value={planHours} onChange={e => setPlanHours(Number(e.target.value) || 1)} type="number" min="1" max="12"
                style={{ ...S.input, maxWidth: 80 }} />
              <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} onClick={makePlan} style={S.smallBtn}>PLAN</motion.button>
            </div>
            {!plan && <div style={{ fontSize: 11, color: 'var(--text-dim)', textAlign: 'center', marginTop: 12 }}>Generate a study plan with the AI exam planner.</div>}
            {(plan?.schedule || plan?.plan || []).map((p, i) => (
              <div key={i} style={{ ...S.card, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontFamily: 'Orbitron', fontSize: 11, color: 'var(--cyan)', letterSpacing: 1 }}>{p.focus || p.topic || p.title || p.subject}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>{p.hours ? `${p.hours}h` : ''}{p.notes ? ` · ${p.notes}` : ''}</div>
                </div>
                <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{p.date || p.day || `Day ${i + 1}`}</span>
              </div>
            ))}
            {plan && typeof plan === 'object' && !plan.schedule && !plan.plan && (
              <div style={S.card}>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, color: '#e0f0e8', margin: 0, fontFamily: 'Rajdhani' }}>
                  {plan.result || plan.text || JSON.stringify(plan, null, 2)}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const S = {
  tab: { display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid', cursor: 'pointer', fontFamily: 'Rajdhani', fontSize: 12, background: 'transparent' },
  card: { background: 'rgba(0,20,16,0.7)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 10, padding: 14 },
  modeBtn: { padding: '6px 18px', borderRadius: 6, border: '1px solid', cursor: 'pointer', fontFamily: 'Orbitron', fontSize: 9, letterSpacing: 1 },
  pomoBtn: { padding: '10px 32px', borderRadius: 8, border: '1px solid rgba(0,255,200,0.3)', background: 'rgba(0,255,200,0.1)', color: 'var(--cyan)', fontFamily: 'Orbitron', fontSize: 11, letterSpacing: 3, cursor: 'pointer' },
  cardFace: { position: 'absolute', inset: 0, borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' },
  cardNav: { padding: '8px 20px', borderRadius: 6, border: '1px solid rgba(0,255,200,0.2)', background: 'rgba(0,255,200,0.05)', color: 'var(--cyan)', fontFamily: 'Orbitron', fontSize: 9, letterSpacing: 2, cursor: 'pointer' },
  smallBtn: { padding: '6px 16px', borderRadius: 6, border: '1px solid rgba(0,255,200,0.3)', background: 'rgba(0,255,200,0.08)', color: 'var(--cyan)', fontFamily: 'Rajdhani', fontSize: 12, cursor: 'pointer' },
  input: { flex: 1, minWidth: 0, background: 'rgba(0,255,200,0.04)', border: '1px solid rgba(0,255,200,0.2)', borderRadius: 6, padding: '8px 10px', color: 'var(--cyan)', fontSize: 12, outline: 'none', fontFamily: 'Rajdhani' },
}
