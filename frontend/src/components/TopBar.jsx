import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { errorsOf } from '../api/client'
import { useAuth } from '../auth/context'
import { Button } from './Button'
import { KnightCrest } from './KnightCrest'
import { Wordmark } from './Wordmark'

// `onLogoutError` receives API errors so each screen can show them where its alerts live.
export function TopBar({ onLogoutError }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [leaving, setLeaving] = useState(false)
  const name = user.profile?.nickname ?? user.username

  async function handleLogout() {
    setLeaving(true)
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch (error) {
      onLogoutError?.(errorsOf(error))
      setLeaving(false)
    }
  }

  return (
    <header className="topbar">
      <Wordmark size="small" />
      <nav className="topbar__nav" aria-label="Main">
        <NavLink to="/games" className="topbar__link">
          Games
        </NavLink>
        <NavLink to="/profile" className="topbar__link">
          Your banner
        </NavLink>
      </nav>
      <div className="topbar__player">
        {user.profile && <KnightCrest avatarKey={user.profile.avatar_key} size={30} title="" />}
        <span className="topbar__name">{name}</span>
        <Button variant="ghost" onClick={handleLogout} pending={leaving} pendingLabel="Logging out…">
          Log out
        </Button>
      </div>
    </header>
  )
}
