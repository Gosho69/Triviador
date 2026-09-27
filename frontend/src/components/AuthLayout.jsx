import { NavLink } from 'react-router-dom'
import { Frame } from './Frame'
import { NightSky } from './NightSky'
import { RealmMap } from './RealmMap'
import { Wordmark } from './Wordmark'

export function AuthLayout({ title, intro, children }) {
  return (
    <main className="auth-layout">
      <NightSky />
      <div className="auth-layout__realm">
        <Wordmark as="h1" />
        <p className="auth-layout__tagline">Answer well, claim territory, hold your castle.</p>
        <RealmMap />
      </div>

      <Frame className="auth-layout__panel" aria-labelledby="auth-title">
        <nav className="auth-tabs" aria-label="Account">
          <NavLink to="/login" className="auth-tabs__tab">
            Sign in
          </NavLink>
          <NavLink to="/register" className="auth-tabs__tab">
            Create account
          </NavLink>
        </nav>
        <h2 id="auth-title" className="panel-title">
          {title}
        </h2>
        <p className="panel-intro">{intro}</p>
        {children}
      </Frame>
    </main>
  )
}
