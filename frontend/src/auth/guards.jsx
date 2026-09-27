import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { LoadingScreen, UnavailableScreen } from '../components/LoadingScreen'
import { useAuth } from './context'

function SessionPending() {
  const { status, retry } = useAuth()
  return status === 'unavailable' ? <UnavailableScreen onRetry={retry} /> : <LoadingScreen />
}

export function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading' || status === 'unavailable') return <SessionPending />
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

// Signed-in users leave guest pages; send them back where they were headed, if anywhere.
export function GuestOnly() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading' || status === 'unavailable') return <SessionPending />
  if (status === 'authenticated') {
    return <Navigate to={location.state?.from?.pathname ?? '/profile'} replace />
  }
  return <Outlet />
}
