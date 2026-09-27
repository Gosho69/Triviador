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
