// Mirrors accounts.models.Profile.Avatar on the backend.
export const KNIGHTS = [
  { key: 'knight-1', name: 'Crimson Knight', colour: 'crimson' },
  { key: 'knight-2', name: 'Azure Knight', colour: 'azure' },
  { key: 'knight-3', name: 'Verdant Knight', colour: 'verdant' },
  { key: 'knight-4', name: 'Golden Knight', colour: 'amber' },
]

export function knightFor(key) {
  return KNIGHTS.find((knight) => knight.key === key) ?? KNIGHTS[0]
}

// On the board a player's colour comes from their seat, so three players never share one.
const SEAT_COLOURS = { 1: 'crimson', 2: 'azure', 3: 'verdant' }

export function seatColour(seat) {
  return SEAT_COLOURS[seat]
}
