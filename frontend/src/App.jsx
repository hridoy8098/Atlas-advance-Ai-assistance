// App.jsx — Atlas 7.0 JARVIS dashboard
import { useEffect, useState } from 'react'
import { Toaster } from 'react-hot-toast'
import MainPage from './pages/MainPage'
import LoginPage from './pages/LoginPage'
import ServerSetup from './components/jarvis/ServerSetup'
import { getHealth } from './services/api'
import useAtlasStore from './store/useAtlasStore'

function App() {
  const [needsServer, setNeedsServer] = useState(false)
  const [setupOpen, setSetupOpen] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)
  const [authRequired, setAuthRequired] = useState(false)
  const [bootMessage, setBootMessage] = useState('ATLAS')
  const isAuthenticated = useAtlasStore(s => s.isAuthenticated)
  const logout = useAtlasStore(s => s.logout)

  useEffect(() => {
    const openSetup = () => setSetupOpen(true)
    window.addEventListener('atlas:open-server-setup', openSetup)
    return () => window.removeEventListener('atlas:open-server-setup', openSetup)
  }, [])

  // Ask the server whether this deployment is public. Cloud servers require
  // the PIN; a local install keeps the dashboard open.
  useEffect(() => {
    const onUnauthorized = () => {
      logout()
      setAuthRequired(true)
      setAuthChecked(true)
    }
    window.addEventListener('atlas:unauthorized', onUnauthorized)

    let cancelled = false
    let retryTimer = null

    // Render's free tier sleeps after 15 idle minutes and needs up to a minute
    // to wake, so a single failed health check is not final.
    const probe = (attempt = 0) => {
      getHealth()
        .then(health => {
          if (cancelled) return
          setAuthRequired(Boolean(health.auth_required))
          setNeedsServer(false)
          setAuthChecked(true)
        })
        .catch(() => {
          if (cancelled) return
          if (attempt < 3) {
            if (attempt === 0) setBootMessage('WAKING ATLAS CLOUD')
            retryTimer = setTimeout(() => probe(attempt + 1), 4000)
            return
          }
          // Nothing answered. Let the user check/paste the API URL, including
          // in the native shell where no URL is baked in.
          setNeedsServer(true)
          setAuthChecked(true)
        })
    }
    probe()

    return () => {
      cancelled = true
      if (retryTimer) clearTimeout(retryTimer)
      window.removeEventListener('atlas:unauthorized', onUnauthorized)
    }
  }, [logout])

  const showLogin = authChecked && authRequired && !isAuthenticated

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0a1420',
            color: '#dbe9f5',
            border: '1px solid rgba(56,189,248,0.25)',
            fontFamily: "'Inter', sans-serif",
            fontSize: '13px',
          },
          success: { iconTheme: { primary: '#38bdf8', secondary: '#0a1420' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0a1420' } },
        }}
      />
      {!authChecked ? (
        <div style={{
          minHeight: '100vh', display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: '#050d16', color: '#38bdf8',
          fontFamily: "'Inter', sans-serif", letterSpacing: '0.35em', fontSize: 18,
          textAlign: 'center', padding: 20,
        }}>
          {bootMessage}
        </div>
      ) : showLogin ? (
        <LoginPage />
      ) : needsServer ? null : (
        <MainPage />
      )}
      {needsServer && (
        <ServerSetup
          blocking
          onConnected={() => setNeedsServer(false)}
        />
      )}
      {setupOpen && (
        <ServerSetup
          onClose={() => setSetupOpen(false)}
          onConnected={() => { setSetupOpen(false); setNeedsServer(false) }}
        />
      )}
    </>
  )
}

export default App
