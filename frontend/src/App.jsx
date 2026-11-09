// App.jsx — Atlas 7.0 JARVIS dashboard (login disabled).
import { useEffect, useState } from 'react'
import { Toaster } from 'react-hot-toast'
import MainPage from './pages/MainPage'
import ServerSetup from './components/jarvis/ServerSetup'
import { getServerUrl, isNativeApp } from './services/api'

function App() {
  const [needsServer, setNeedsServer] = useState(
    () => isNativeApp() && !getServerUrl()
  )
  const [setupOpen, setSetupOpen] = useState(false)

  useEffect(() => {
    const openSetup = () => setSetupOpen(true)
    window.addEventListener('atlas:open-server-setup', openSetup)
    return () => window.removeEventListener('atlas:open-server-setup', openSetup)
  }, [])

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
      <MainPage />
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
