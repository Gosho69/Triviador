import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorsOf, gamesApi } from '../api/client'
import { Button } from '../components/Button'
import { FormAlert } from '../components/FormAlert'
import { Frame } from '../components/Frame'
import { NightSky } from '../components/NightSky'
import { SeatMarks } from '../components/SeatMarks'
import { TopBar } from '../components/TopBar'
import { gameTitle, isFull, seatsOf } from './games'
import { usePolling } from './usePolling'

export function LobbyPage() {
  const navigate = useNavigate()
  const games = usePolling(gamesApi.list)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(null)

  // Create and join both lead straight into the game's room.
  async function enter(key, action) {
    setBusy(key)
    setErrors({})
    try {
      const game = await action()
      navigate(`/games/${game.id}`)
    } catch (error) {
      setErrors(errorsOf(error))
      setBusy(null)
      games.refresh()
    }
  }

  const all = games.data ?? []
  const mine = all.filter((game) => game.is_member)
  const open = all.filter((game) => !game.is_member && !isFull(game))
  // An action's own error wins; otherwise show why the list could not be refreshed.
  const alert = Object.keys(errors).length > 0 ? errors : games.error ? errorsOf(games.error) : {}

  return (
    <div className="page-screen">
      <NightSky />
      <TopBar onLogoutError={setErrors} />

      <main className="hall">
        <h1 className="page-title">Games</h1>
        <p className="page-intro">
          Three knights per game. Raise a banner and wait for two more, or take a free seat in one already raised.
        </p>

        <FormAlert errors={alert} />

        {mine.length > 0 && (
          <Frame className="hall__panel" aria-labelledby="mine-title">
            <h2 id="mine-title" className="panel-title">
              Your games
            </h2>
            <ul className="game-list">
              {mine.map((game) => (
                <GameRow key={game.id} game={game}>
                  <Link to={`/games/${game.id}`} className="button button--quiet">
                    {game.status === 'in_progress' ? 'View map' : 'Open'}
                  </Link>
                </GameRow>
              ))}
            </ul>
          </Frame>
        )}

        <Frame className="hall__panel" aria-labelledby="open-title">
          <div className="panel-heading">
            <h2 id="open-title" className="panel-title">
              Open games
            </h2>
            <Button
              onClick={() => enter('create', gamesApi.create)}
              pending={busy === 'create'}
              pendingLabel="Raising…"
              disabled={busy !== null}
            >
              Raise a banner
            </Button>
          </div>

          {games.loading ? (
            <GameListSkeleton />
          ) : !games.data ? null : open.length === 0 ? (
            <p className="empty-note">
              No banners are waiting for knights. Raise one and the next players to arrive can join you.
            </p>
          ) : (
            <ul className="game-list">
              {open.map((game) => (
                <GameRow key={game.id} game={game}>
                  <Button
                    onClick={() => enter(game.id, () => gamesApi.join(game.id))}
                    pending={busy === game.id}
                    pendingLabel="Joining…"
                    disabled={busy !== null}
                  >
                    Join
                  </Button>
                </GameRow>
              ))}
            </ul>
          )}
        </Frame>
      </main>
    </div>
  )
}

function GameRow({ game, children }) {
  const status =
    game.status === 'in_progress' ? 'In progress' : `${game.players.length} of ${game.seats} seats taken`

  return (
    <li className="game-row">
      <div className="game-row__text">
        <p className="game-row__title">{gameTitle(game)}</p>
        <p className="game-row__status">{status}</p>
      </div>
      <SeatMarks seats={seatsOf(game)} players={game.players} />
      <div className="game-row__action">{children}</div>
    </li>
  )
}

function GameListSkeleton() {
  return (
    <ul className="game-list" aria-busy="true" aria-label="Loading games">
      {[0, 1].map((row) => (
        <li key={row} className="game-row game-row--skeleton" aria-hidden="true">
          <span className="skeleton skeleton--text" />
          <span className="skeleton skeleton--marks" />
        </li>
      ))}
    </ul>
  )
}
