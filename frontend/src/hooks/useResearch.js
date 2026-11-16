import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'

/**
 * Loads a research job and polls the backend while it is queued/running.
 * Stops polling when the job reaches a terminal state; tolerates brief network blips.
 */
export function useResearch(id) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => setTick((t) => t + 1), [])
  const patchData = useCallback((fn) => setState((s) => (s.data ? { ...s, data: fn(s.data) } : s)), [])

  useEffect(() => {
    let cancelled = false
    let timer
    let failures = 0
    const ctrl = new AbortController()
    setState((s) => ({ data: s.data?.id === id ? s.data : null, error: null, loading: true }))

    async function poll() {
      try {
        const data = await api.getResearch(id, ctrl.signal)
        if (cancelled) return
        failures = 0
        setState({ data, error: null, loading: false })
        if (data.status === 'queued' || data.status === 'running') {
          timer = setTimeout(poll, data.status === 'queued' ? 800 : 1500)
        }
      } catch (e) {
        if (cancelled || e?.name === 'AbortError') return
        failures += 1
        if (e.status === 404 || failures >= 5) {
          setState((s) => ({ data: e.status === 404 ? null : s.data, error: e, loading: false }))
          return
        }
        timer = setTimeout(poll, 1500 * failures)
      }
    }
    poll()
    return () => {
      cancelled = true
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [id, tick])

  return { ...state, reload, patchData }
}
