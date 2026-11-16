import { useCallback, useEffect, useState } from 'react'

function parse(hash) {
  const path = (hash || '').replace(/^#/, '') || '/'
  const parts = path.split('/').filter(Boolean)
  if (parts[0] === 'research' && parts[1]) return { name: 'research', id: decodeURIComponent(parts[1]) }
  if (parts[0] === 'history') return { name: 'history' }
  if (parts[0] === 'saved') return { name: 'saved' }
  if (parts[0] === 'settings') return { name: 'settings' }
  return { name: 'home' }
}

/** Tiny hash router: URLs like #/research/abc survive a refresh and work with the back button. */
export function useHashRoute() {
  const [route, setRoute] = useState(() => parse(window.location.hash))

  useEffect(() => {
    const onChange = () => {
      setRoute(parse(window.location.hash))
      window.scrollTo({ top: 0 })
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  const navigate = useCallback((to) => {
    const target = to.startsWith('#') ? to : `#${to}`
    if (window.location.hash === target) setRoute(parse(target))
    else window.location.hash = target
  }, [])

  return { route, navigate }
}
