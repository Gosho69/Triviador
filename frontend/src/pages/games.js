function hostOf(game) {
  return game.players.find((player) => player.is_host)
}

export function gameTitle(game) {
  const host = hostOf(game)
  return host ? `${host.nickname}’s game` : `Game #${game.id}`
}

// Seat numbers 1..n; the number of seats comes from the server.
export function seatsOf(game) {
  return Array.from({ length: game.seats }, (_, index) => index + 1)
}

export function isFull(game) {
  return game.players.length >= game.seats
}
