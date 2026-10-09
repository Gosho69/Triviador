import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorsOf, gamesApi } from '../api/client'
import { Button } from '../components/Button'
import { FormAlert } from '../components/FormAlert'
import { Frame } from '../components/Frame'
import { GameBoard } from '../components/GameBoard'
import { KnightCrest } from '../components/KnightCrest'
import { NightSky } from '../components/NightSky'
import { OpenSeatShield } from '../components/SeatMarks'
import { TopBar } from '../components/TopBar'
import { seatColour } from '../knights'
import { gameTitle, isFull, seatsOf } from './games'
import { usePolling } from './usePolling'

// Only a waiting room changes on its own; once a game has started, closed or gone out of
// sight (404: disbanded, or started without you), stop asking.
const isWaiting = (game, error) => error?.status !== 404 && (!game || game.status === 'waiting')

export function GamePage({ id }) {
  const game = usePolling(() => gamesApi.get(id), { enabled: isWaiting })
  const [errors, setErrors] = useState({})

  let content
  if (game.loading) {
    content = <p className="room__status">Loading the game…</p>
  } else if (game.error?.status === 404) {
    content = <Closed title="Game not found" text="It may have been disbanded, or it has started without you." />
  } else if (!game.data) {
    content = <FormAlert errors={errorsOf(game.error)} />
  } else if (game.data.status === 'waiting') {
    content = <WaitingRoom game={game.data} onChange={game.replace} onFailure={game.refresh} />
  } else if (game.data.status === 'in_progress') {
    content = <StartedGame game={game.data} />
  } else {
    const text = game.data.status === 'cancelled' ? 'The host disbanded this game.' : 'This game has ended.'
    content = <Closed title={gameTitle(game.data)} text={text} />
  }

  return (
    <div className="page-screen">
      <NightSky />
      <TopBar onLogoutError={setErrors} />
      <main className="room">
        <Link to="/games" className="back-link">
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
            <path d="M10 3 5 8l5 5" />
          </svg>
          All games
        </Link>
        <FormAlert errors={errors} />
        {content}
      </main>
    </div>
  )
}

function Closed({ title, text }) {
  return (
    <Frame className="room__panel room__panel--narrow" aria-labelledby="closed-title">
      <h1 id="closed-title" className="panel-title">
        {title}
      </h1>
      <p className="panel-intro">{text}</p>
      <Link to="/games" className="button button--gold">
        Find another game
      </Link>
    </Frame>
  )
}

function WaitingRoom({ game, onChange, onFailure }) {
  const navigate = useNavigate()
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(null)
  const [confirmDisband, setConfirmDisband] = useState(false)
  const bySeat = new Map(game.players.map((player) => [player.seat, player]))
  const missing = game.seats - game.players.length

  async function run(key, action, { leave = false } = {}) {
    setBusy(key)
    setErrors({})
    try {
      const result = await action()
      if (leave) return navigate('/games')
      onChange(result)
    } catch (error) {
      setErrors(errorsOf(error))
      onFailure()
    }
    setBusy(null)
  }

  return (
    <Frame className="room__panel" aria-labelledby="room-title">
      <h1 id="room-title" className="panel-title">
        {gameTitle(game)}
      </h1>
      <p className="panel-intro" aria-live="polite">
        {missing > 0
          ? `Waiting for ${missing} more ${missing === 1 ? 'knight' : 'knights'}. This page updates on its own.`
          : game.is_host
            ? 'All three seats are taken. Start when you are ready.'
            : 'All three seats are taken. Waiting for the host to start.'}
      </p>

      <ol className="seats">
        {seatsOf(game).map((seat) => (
          <Seat key={seat} seat={seat} player={bySeat.get(seat)} />
        ))}
      </ol>

      <FormAlert errors={errors} />

      <div className="room__actions">
        {game.is_host ? (
          <>
            <Button
              onClick={() => run('start', () => gamesApi.start(game.id))}
              pending={busy === 'start'}
              pendingLabel="Starting…"
              disabled={busy !== null || missing > 0}
            >
              Start game
            </Button>
            {confirmDisband ? (
              <div className="confirm" role="group" aria-label="Disband this game?">
                <span className="confirm__question">Disband this game?</span>
                <Button
                  variant="danger"
                  onClick={() => run('cancel', () => gamesApi.cancel(game.id), { leave: true })}
                  pending={busy === 'cancel'}
                  pendingLabel="Disbanding…"
                  disabled={busy !== null}
                >
                  Disband
                </Button>
                <Button variant="quiet" onClick={() => setConfirmDisband(false)} disabled={busy !== null}>
                  Keep it
                </Button>
              </div>
            ) : (
              <Button variant="quiet" onClick={() => setConfirmDisband(true)} disabled={busy !== null}>
                Disband game
              </Button>
            )}
          </>
        ) : game.is_member ? (
          <Button
            variant="quiet"
            onClick={() => run('leave', () => gamesApi.leave(game.id), { leave: true })}
            pending={busy === 'leave'}
            pendingLabel="Leaving…"
            disabled={busy !== null}
          >
            Leave game
          </Button>
        ) : isFull(game) ? (
          <p className="room__note">Every seat is taken.</p>
        ) : (
          <Button
            onClick={() => run('join', () => gamesApi.join(game.id))}
            pending={busy === 'join'}
            pendingLabel="Joining…"
            disabled={busy !== null}
          >
            Take a seat
          </Button>
        )}
      </div>
    </Frame>
  )
}

function Seat({ seat, player }) {
  return (
    <li className="seat">
      {player ? (
        <div key={player.nickname} className="seat__body seat__body--taken">
          <KnightCrest avatarKey={player.avatar_key} colour={seatColour(seat)} size={64} title="" />
          <p className="seat__name">{player.nickname}</p>
          <p className="seat__role">{[player.is_host && 'Host', player.is_you && 'You'].filter(Boolean).join(' · ')}</p>
        </div>
      ) : (
        <div className="seat__body">
          <OpenSeatShield size={64} />
          <p className="seat__name seat__name--open">Open seat</p>
          <p className="seat__role" />
        </div>
      )}
    </li>
  )
}

function Health({ health, max_health: max }) {
  return (
    <p className="health" role="img" aria-label={`Health ${health} of ${max}`}>
      {Array.from({ length: max }, (_, index) => (
        <span key={index} className="health__pip" data-lost={index >= health || undefined} />
      ))}
    </p>
  )
}

function StartedGame({ game }) {
  const territories = game.board?.territories ?? []
  const capitals = new Map(territories.filter((t) => t.capital).map((t) => [t.owner_seat, t]))
  const neutral = territories.filter((t) => t.owner_seat === null).length

  return (
    <div className="battlefield">
      <div className="battlefield__heading">
        <h1 className="page-title">{gameTitle(game)}</h1>
        <p className="page-intro">
          The game has started. Each knight holds a capital; {neutral} {neutral === 1 ? 'territory is' : 'territories are'} still
          unclaimed.
        </p>
      </div>

      <Frame className="battlefield__map" aria-label="Map">
        <GameBoard territories={territories} players={game.players} />
      </Frame>

      <Frame as="aside" className="battlefield__legend" aria-labelledby="legend-title">
        <h2 id="legend-title" className="panel-title panel-title--small">
          Knights
        </h2>
        <ul className="legend">
          {game.players.map((player) => {
            const capital = capitals.get(player.seat)
            return (
              <li key={player.seat} className="legend__player" data-colour={seatColour(player.seat)}>
                <KnightCrest avatarKey={player.avatar_key} colour={seatColour(player.seat)} size={36} title="" />
                <div className="legend__text">
                  <p className="legend__name">
                    {player.nickname}
                    {player.is_you && <span className="legend__you"> · You</span>}
                  </p>
                  {capital && (
                    <>
                      <p className="legend__capital">Capital {capital.name}</p>
                      <Health {...capital.capital} />
                    </>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      </Frame>
    </div>
  )
}
