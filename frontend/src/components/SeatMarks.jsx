import { seatColour } from '../knights'
import { KnightCrest } from './KnightCrest'

const SHIELD = 'M4 6H60V34C60 52 46 64 32 70C18 64 4 52 4 34Z'

// Outline of an unclaimed seat, the same shield shape as a knight's crest.
export function OpenSeatShield({ size }) {
  return (
    <svg className="open-seat" width={size} height={size * (72 / 64)} viewBox="0 0 64 72" aria-hidden="true">
      <path d={SHIELD} />
    </svg>
  )
}

// One small shield per seat: the player's crest, or an outline while the seat is open.
export function SeatMarks({ seats, players }) {
  const bySeat = new Map(players.map((player) => [player.seat, player]))
  return (
    <ul className="seat-marks" aria-label={`${players.length} of ${seats.length} seats taken`}>
      {seats.map((seat) => {
        const player = bySeat.get(seat)
        return (
          <li key={seat}>
            {player ? (
              <KnightCrest avatarKey={player.avatar_key} colour={seatColour(seat)} size={24} title={player.nickname} />
            ) : (
              <OpenSeatShield size={24} />
            )}
          </li>
        )
      })}
    </ul>
  )
}
