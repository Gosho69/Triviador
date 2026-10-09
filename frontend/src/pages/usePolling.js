import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/context'

// Loads data now and again every `interval` ms while `enabled` and the tab is visible.
// `enabled` may be a function of the latest data and error, e.g. to stop once a game has started.
// Responses that arrive after a newer load (or after `replace`) are dropped, so an action's
// result is never overwritten by an older poll.
export function usePolling(load, { interval = 4000, enabled = true } = {}) {
  const { retry: recheckSession } = useAuth()
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const loadRef = useRef(load)
  const latest = useRef(0)

  useEffect(() => {
    loadRef.current = load
  })

  const refresh = useCallback(async () => {
    const request = ++latest.current
    try {
      const data = await loadRef.current()
      if (request === latest.current) setState({ data, error: null, loading: false })
    } catch (error) {
      if (request !== latest.current) return
      // Polls only read, so 401/403 means the session ended: let the auth guard send the player to sign in.
      if (error.status === 401 || error.status === 403) return recheckSession()
      setState((current) => ({ ...current, error, loading: false }))
    }
  }, [recheckSession])

  const replace = useCallback((data) => {
    latest.current += 1
    setState({ data, error: null, loading: false })
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const active = typeof enabled === 'function' ? enabled(state.data, state.error) : enabled

  useEffect(() => {
    if (!active) return undefined
    const poll = () => {
      if (!document.hidden) refresh()
    }
    const timer = setInterval(poll, interval)
    document.addEventListener('visibilitychange', poll)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', poll)
    }
  }, [active, interval, refresh])

  return { ...state, refresh, replace }
}
