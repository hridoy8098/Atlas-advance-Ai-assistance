// src/pages/LoginPage.jsx
import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { verifyPin } from '../services/api'
import useAtlasStore from '../store/useAtlasStore'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [pin, setPin] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [shake, setShake] = useState(false)
  const { setAuthenticated } = useAtlasStore()
  const navigate = useNavigate()
  const refs = [useRef(), useRef(), useRef(), useRef(), useRef(), useRef()]

  useEffect(() => { refs[0].current?.focus() }, [])

  const handleKey = (i, val) => {
    if (!/^\d?$/.test(val)) return
    const next = [...pin]
    next[i] = val
    setPin(next)
    if (val && i < 5) refs[i + 1].current?.focus()
    if (next.every(d => d !== '')) submitPin(next.join(''))
  }

  const handleBackspace = (i, e) => {
    if (e.key === 'Backspace' && !pin[i] && i > 0) {
      refs[i - 1].current?.focus()
    }
  }

  const submitPin = async (pinStr) => {
    setLoading(true)
    try {
      const res = await verifyPin(pinStr)
      if (res.success) {
        setAuthenticated(res.session_token)
        navigate('/')
      } else {
        setShake(true)
        toast.error(res.reason || 'Wrong PIN')
        setPin(['', '', '', '', '', ''])
        refs[0].current?.focus()
        setTimeout(() => setShake(false), 600)
      }
    } catch {
      toast.error('Server not reachable')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      {/* Scanline */}
      <div style={styles.scanline} />

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        style={styles.card}
      >
        {/* Logo */}
        <div style={styles.logo}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
            style={styles.ring}
          />
          <span style={styles.logoText}>A</span>
        </div>

        <h1 style={styles.title}>ATLAS 7.0</h1>
        <p style={styles.subtitle}>IDENTITY VERIFICATION</p>

        {/* PIN Inputs */}
        <motion.div
          animate={shake ? { x: [-8, 8, -8, 8, 0] } : {}}
          transition={{ duration: 0.4 }}
          style={styles.pinRow}
        >
          {pin.map((d, i) => (
            <input
              key={i}
              ref={refs[i]}
              type="password"
              maxLength={1}
              value={d}
              onChange={e => handleKey(i, e.target.value)}
              onKeyDown={e => handleBackspace(i, e)}
              style={{
                ...styles.pinInput,
                borderColor: d ? 'var(--cyan)' : 'var(--cyan-border)',
                boxShadow: d ? '0 0 10px rgba(0,255,255,0.4)' : 'none',
              }}
            />
          ))}
        </motion.div>

        {loading && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={styles.verifying}
          >
            VERIFYING...
          </motion.p>
        )}

        <p style={styles.hint}>Enter your 6-digit PIN</p>
      </motion.div>
    </div>
  )
}

const styles = {
  page: {
    height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'radial-gradient(ellipse at center, #001428 0%, #000a14 100%)',
    position: 'relative', overflow: 'hidden',
  },
  scanline: {
    position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
    background: 'linear-gradient(90deg, transparent, rgba(0,255,255,0.4), transparent)',
    animation: 'scanline 4s linear infinite',
    pointerEvents: 'none',
  },
  card: {
    background: 'rgba(0,15,30,0.9)', border: '1px solid rgba(0,255,255,0.3)',
    borderRadius: '16px', padding: '50px 40px', textAlign: 'center',
    backdropFilter: 'blur(20px)', minWidth: '360px',
    boxShadow: '0 0 60px rgba(0,255,255,0.1), inset 0 0 30px rgba(0,255,255,0.03)',
  },
  logo: {
    position: 'relative', width: '80px', height: '80px',
    margin: '0 auto 20px', display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  ring: {
    position: 'absolute', inset: 0,
    border: '2px solid transparent',
    borderTopColor: 'var(--cyan)', borderRightColor: 'rgba(0,255,255,0.3)',
    borderRadius: '50%',
  },
  logoText: {
    fontFamily: 'Orbitron', fontSize: '32px', color: 'var(--cyan)',
    textShadow: '0 0 20px var(--cyan)',
  },
  title: {
    fontFamily: 'Orbitron', fontSize: '24px', color: 'var(--cyan)',
    textShadow: '0 0 20px var(--cyan)', marginBottom: '6px',
  },
  subtitle: {
    fontFamily: 'Rajdhani', fontSize: '12px', color: 'var(--text-dim)',
    letterSpacing: '3px', marginBottom: '36px',
  },
  pinRow: { display: 'flex', gap: '10px', justifyContent: 'center', marginBottom: '20px' },
  pinInput: {
    width: '46px', height: '52px', textAlign: 'center', fontSize: '24px',
    background: 'rgba(0,255,255,0.05)', border: '1px solid',
    borderRadius: '8px', color: 'var(--cyan)', outline: 'none',
    fontFamily: 'Orbitron', transition: 'all 0.2s',
  },
  verifying: {
    fontFamily: 'Orbitron', fontSize: '11px', color: 'var(--cyan)',
    letterSpacing: '3px', marginBottom: '12px', animation: 'blink 1s infinite',
  },
  hint: { fontSize: '12px', color: 'var(--text-dim)', letterSpacing: '1px' },
}
