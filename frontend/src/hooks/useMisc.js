import { useEffect, useState } from 'react'
import { api } from '../services/api'

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false)
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!mq) return
    const on = (e) => setReduced(e.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return reduced
}

export function hasWebGL() {
  try {
    const c = document.createElement('canvas')
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')))
  } catch {
    return false
  }
}

/** Backend health: tells the UI if the server is unreachable or missing API keys. */
export function useHealth() {
  const [state, setState] = useState({ loading: true, health: null, error: null })
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const ctrl = new AbortController()
    setState((s) => ({ ...s, loading: true }))
    api.health(ctrl.signal)
      .then((health) => setState({ loading: false, health, error: null }))
      .catch((error) => { if (error?.name !== 'AbortError') setState({ loading: false, health: null, error }) })
    return () => ctrl.abort()
  }, [tick])
  return { ...state, refresh: () => setTick((t) => t + 1) }
}

export function useElapsed(startIso, active) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [active])
  const start = startIso ? new Date(startIso).getTime() : now
  return Math.max(0, (now - start) / 1000)
}
