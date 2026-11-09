// App.jsx — Atlas 7.0 JARVIS dashboard
import { useEffect, useState } from 'react'
import { Toaster } from 'react-hot-toast'
import MainPage from './pages/MainPage'
import LoginPage from './pages/LoginPage'
import ServerSetup from './components/jarvis/ServerSetup'
import { getHealth, getServerUrl, isNativeApp } from './services/api'
import useAtlasStore from './store/useAtlasStore'

function App() {
  const [needsServer, setNeedsServer] = useState(false)
  const [setupOpen, setSetupOpen] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)
  const [authRequired, setAuthRequired] = useState(false)
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
    getHealth()
      .then(health => {
        setAuthRequired(Boolean(health.auth_required))
        setNeedsServer(false)
      })
      .catch(() => {
        // Static hosting (GitHub Pages / HF) has no backend of its own.
        // Ask for the API server URL once, unless the user already saved one.
        if (!isNativeApp() && !getServerUrl()) setNeedsServer(true)
      })
      .finally(() => setAuthChecked(true))
    return () => window.removeEventListener('atlas:unauthorized', onUnauthorized)
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
        }}>
          ATLAS
        </div>
      ) : showLogin ? (
        <LoginPage />
      ) : (
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
