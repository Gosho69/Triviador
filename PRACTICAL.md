# Waiting Room Plan

## Data

- `WaitingRoomEntry`: `user` (one-to-one), `joined_at`.
- `GamePlayer.color`: `red`, `blue`, `green`, unique per game.
- Status mapping: `waiting` = `WAITING`, `active` = `IN_PROGRESS`, `completed` = `FINISHED`.

## Operations

- `join_waiting_room(user)`: reject if already waiting or in a `WAITING`/`IN_PROGRESS` game.
- `leave_waiting_room(user)`: delete own entry; no entry means no change.
- `form_game()`: in one transaction, pick 3 random eligible entries, create a `WAITING` game and 3 players with different colors and score 0, delete the 3 entries. Fewer than 3 means no change.

## Trigger

- `form_game()` runs after every successful join.

## API

- `POST /api/games/waiting-room/join/`
- `POST /api/games/waiting-room/leave/`

## Tests

- **Five users waiting:** `form_game()` creates one new `WAITING` game with 3 players. The 3 players are different users who were waiting, each has a different color, and all have score 0. These 3 leave the waiting room and the other 2 are still waiting.
- **Two users waiting:** `form_game()` creates nothing. The number of games, players and waiting entries stays the same.
