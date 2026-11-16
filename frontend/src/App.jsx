import { useCallback, useEffect, useState } from 'react'
import Background from './components/Background'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import HomePage from './pages/HomePage'
import ResearchPage from './pages/ResearchPage'
import HistoryPage from './pages/HistoryPage'
import SettingsPage from './pages/SettingsPage'
import { useHashRoute } from './hooks/useHashRoute'
import { api } from './services/api'

export default function App() {
  const { route, navigate } = useHashRoute()
  const [menuOpen, setMenuOpen] = useState(false)
  const [recent, setRecent] = useState([])
  const [recentTick, setRecentTick] = useState(0)
  const refreshRecent = useCallback(() => setRecentTick((t) => t + 1), [])

  // Recent list for the sidebar. Failures are silent: the main views show their own errors.
  useEffect(() => {
    const ctrl = new AbortController()
    api.history({ limit: 6 }, ctrl.signal).then(setRecent).catch(() => {})
    return () => ctrl.abort()
  }, [recentTick, route.name, route.id])

  const closeMenu = useCallback(() => setMenuOpen(false), [])

  let page
  switch (route.name) {
    case 'research': page = <ResearchPage key={route.id} id={route.id} navigate={navigate} onChanged={refreshRecent} />; break
    case 'history': page = <HistoryPage key="history" saved={false} onChanged={refreshRecent} />; break
    case 'saved': page = <HistoryPage key="saved" saved onChanged={refreshRecent} />; break
    case 'settings': page = <SettingsPage />; break
    default: page = <HomePage navigate={navigate} onStarted={refreshRecent} />
  }

  return (
    <>
      <Background />
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[100] focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-on-accent" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus() }}>
        Skip to content
      </a>
      {/* A floating frame of dark glass over the star field (full-bleed on phones). */}
      <div className="relative z-10 lg:p-4">
        <div className="panel mx-auto flex min-h-screen min-w-0 max-w-[110rem] flex-col overflow-clip lg:min-h-[calc(100vh-2rem)] lg:flex-row lg:rounded-[1.75rem] lg:border lg:border-line-strong">
          <Sidebar route={route} recent={recent} open={menuOpen} onOpen={() => setMenuOpen(true)} onClose={closeMenu} />
          <div className="flex min-w-0 flex-1 flex-col">
            <TopBar />
            <main id="main" tabIndex={-1} className="min-w-0 flex-1 px-4 pb-16 pt-6 outline-none sm:px-8 lg:pt-4">
              {page}
            </main>
          </div>
        </div>
      </div>
    </>
  )
}
