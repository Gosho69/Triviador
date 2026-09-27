import { useCallback, useEffect, useMemo, useState } from 'react'
import { authApi, isCsrfError } from '../api/client'
import { AuthContext } from './context'

export function AuthProvider({ children }) {
  // status: 'loading' until the session is checked, then 'authenticated' or 'anonymous'.
  // 'unavailable' means the check itself failed (server down), so we don't pretend to be logged out.
  const [state, setState] = useState({ status: 'loading', user: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    authApi
      .me()
      .then((user) => active && setState({ status: 'authenticated', user }))
      .catch((error) => {
        if (!active) return
        const signedOut = error.status === 401 || error.status === 403
        setState({ status: signedOut ? 'anonymous' : 'unavailable', user: null })
      })
    return () => {
      active = false
    }
  }, [attempt])

  const retry = useCallback(() => {
    setState({ status: 'loading', user: null })
    setAttempt((count) => count + 1)
  }, [])

  const signIn = useCallback((user) => setState({ status: 'authenticated', user }), [])

  const login = useCallback(async (credentials) => signIn(await authApi.login(credentials)), [signIn])

  const register = useCallback(async (payload) => signIn(await authApi.register(payload)), [signIn])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch (error) {
      // A session that already expired is as good as logged out; a CSRF failure is not.
      if (error.status !== 403 || isCsrfError(error.status, error.errors)) throw error
    }
    setState({ status: 'anonymous', user: null })
  }, [])

  const updateProfile = useCallback(async (changes) => {
    const user = await authApi.updateProfile(changes)
    setState({ status: 'authenticated', user })
    return user
  }, [])

  const value = useMemo(
    () => ({ ...state, login, register, logout, updateProfile, retry }),
    [state, login, register, logout, updateProfile, retry],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
