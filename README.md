# Triviador

Trivia conquest game: Django + DRF backend (`backend/`), React + Vite frontend (`frontend/`).

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

| App | Milestone | Contents |
|---|---|---|
| `accounts` | M1 | Custom user, profile, auth API |
| `questions` | M2 | Categories, choice and numeric questions, question bank fixture |
| `games` | M3, M5 | `Game`, `GamePlayer`, `Round`, `RoundAnswer`; game initialization and player changes |
| `territories` | M4 | Project map, `Territory`, `Adjacency`, `Capital` |

## M4 — Territories and map

### Project map

The project uses **one fixed map of 18 territories** (`backend/territories/map.py`). Every game gets
its own `Territory` records built from this definition, so names, slugs, count and borders are the
same in all games; only the game state (owner, score, capitals) differs.

Layout: three rows of six regions (north, middle, south).

| Row | Territories (name / slug) |
|---|---|
| North | Скали `skali` · Дунавия `dunaviya` · Житно поле `zhitno-pole` · Левента `leventa` · Пеликания `pelikania` · Калиакра `kaliakra` |
| Middle | Средец `sredets` · Балкания `balkania` · Розова долина `rozova-dolina` · Мадара `madara` · Златен грозд `zlaten-grozd` · Слънчево `slanchevo` |
| South | Пирина `pirina` · Езера `ezera` · Кукери `kukeri` · Чуден край `chuden-kray` · Каракачан `karakachan` · Царево `tsarevo` |

### Borders (31)

| Territory | Neighbours |
|---|---|
| Скали | Дунавия, Средец |
| Дунавия | Скали, Житно поле, Балкания, Розова долина |
| Житно поле | Дунавия, Левента, Розова долина |
| Левента | Житно поле, Пеликания, Мадара, Златен грозд |
| Пеликания | Левента, Калиакра, Златен грозд |
| Калиакра | Пеликания, Слънчево |
| Средец | Скали, Балкания, Пирина |
| Балкания | Средец, Розова долина, Дунавия, Езера, Кукери |
| Розова долина | Балкания, Мадара, Житно поле, Дунавия, Кукери |
| Мадара | Розова долина, Златен грозд, Левента, Чуден край, Каракачан |
| Златен грозд | Мадара, Слънчево, Пеликания, Левента, Каракачан |
| Слънчево | Златен грозд, Калиакра, Царево |
| Пирина | Средец, Езера |
| Езера | Пирина, Кукери, Балкания |
| Кукери | Езера, Чуден край, Розова долина, Балкания |
| Чуден край | Кукери, Каракачан, Мадара |
| Каракачан | Чуден край, Царево, Златен грозд, Мадара |
| Царево | Каракачан, Слънчево |

### Rules

Map definition (`validate_map`, also run as system check `territories.E001` on every `manage.py` command):

- 9–21 territories, multiple of 3 (this project: 18);
- unique names and slugs; borders only between known territories;
- borders are symmetric, never to self, never listed twice (A–B and B–A are the same border);
- every territory has at least 2 neighbours and the graph is connected;
- at least one triple of pairwise non-adjacent territories exists for the starting capitals
  (e.g. Скали, Калиакра, Царево) — checked deterministically, nothing is chosen.

Game records:

- `Territory`: name and slug unique per game, owner must be a player of the same game (or empty),
  score ≥ 0, neighbours only within the same game. Self and cross-game borders are rejected on every
  insert path (`neighbors.add()`, `Adjacency.objects.create/bulk_create`, `full_clean()`), and a
  database constraint also blocks self-borders.
- `Capital`: one per player and one per territory, health 0–3 (default 3; 0 = destroyed, record kept),
  player and territory in the same game. A standing capital (health > 0) must be on a territory
  owned by its player, and that territory cannot change owner while it stands; a destroyed capital may
  stay on a conquered territory. Capitals never border each other (they keep their non-adjacent
  starting positions). The game is derived from the territory.
- `validate_game_map(game)` checks that a game's records match the project map exactly (territories,
  names and borders, both directions). It is read-only.

Database constraints guard uniqueness and numeric ranges; cross-row rules live in `clean()`, which
runs through `full_clean()` (Admin forms do this automatically; a plain `save()` does not).

Access: `game.territories.all()`, `player.territories.all()`, `Capital.for_player(player)` (returns
`None` when the player has no capital).

### Admin

Territories (search by name/slug, filter by game/owner) and capitals (search by player/territory,
filter by game) are listed in Django Admin. Records cannot be added or deleted there directly (they
are removed only when their game is deleted), and game,
name, slug, owner, neighbours, player and territory are read-only; only territory score and capital
health are editable, with the same validation.

## M05 — Game initialization

Initialization turns a waiting game into a playable one in a single, explicit operation: it builds the
game's own copy of the project map, gives each player a capital and starts the game. Creating a
`Game` never does this by itself.

### How to trigger it

| Where | How |
|---|---|
| Command line | `python manage.py initialize_game <game_id> [--seed N]` (prints the capitals; `--seed` makes the capital choice reproducible) |
| Django Admin | Games → select games → action **Initialize selected games** (one success/error message per game) |
| Code | `games.services.initialize_game(game, rng=None)` |

Players join and leave through `games.services.add_player(game, user)` and `remove_player(player)`.

### Preconditions (otherwise rejected, nothing changes)

| Rule | Error code |
|---|---|
| Game status is `waiting` (read from the database, not from the passed instance) | `invalid_status` |
| Exactly 3 players | `invalid_player_count` |
| The game has no territories or capitals yet (a partial state is never repaired) | `already_initialized` |
| The map definition passes the M4 rules (`validate_map`) | `invalid_map` (+ the M4 codes) |
| Three pairwise non-adjacent territories exist (normally already caught by `validate_map`) | `no_capital_assignment` |

Errors are `django.core.exceptions.ValidationError`s; the command turns them into `CommandError`.

### Result

| Data | After initialization |
|---|---|
| Game | `status = in_progress` (this project's "active" state), `started_at` set |
| Territories | the 18 territories of the project map, as new records of this game |
| Borders | the 31 borders of the map, stored in both directions, only within the game |
| Capitals | 3, one per player, `health = 3`; the capital territory is owned by its player |
| Other territories | 15 neutral (no owner) |
| Scores | every territory score 0; player scores unchanged |
| Rounds | not created or changed |

The map is never chosen per game: every game gets the same names and borders from
`territories/map.py`, but its own records, so changing one game never affects another.
"Completed" games in the spec are `finished` or `cancelled` here; neither can be initialized.

### Capitals

All groups of three pairwise non-adjacent territories (checked over all three pairs on the border
graph) are listed, one group is picked at random and shuffled across the players, so every valid
assignment is equally likely and nothing depends on the order of players or territories. Production
uses `random.SystemRandom`; tests inject a seeded `random.Random` or a stub. Two games may get the
same capitals.

### Atomicity

Everything runs in one `transaction.atomic()` block: building the map, assigning capitals, a final
`validate_game_map()` check and the status change. Any error, including an unexpected one, rolls
back every change of that attempt, so a game is never `in_progress` with a partial map or missing
capitals. A second attempt is rejected (`invalid_status`, or `already_initialized` if the status was
reset by hand) without adding, moving or reassigning anything. Database constraints back this up:
territory slug and name are unique per game, and a player or territory has at most one capital.

### Players after the start

`add_player` and `remove_player` only work on waiting games (`invalid_status` otherwise).
`add_player` also refuses a user who has already joined (`already_joined`) and a fourth player
(`game_full`).

The admin enforces the same rules on the server, not only in the form it shows:

- The players inline becomes read-only once a game has started. Its formset re-reads the game's
  status from the database when saving, so a form opened before the start cannot add or delete
  players afterwards. It also rejects more than 3 players.
- The status field can only be changed by hand to **Finished** or **Cancelled**, which also sets
  `finished_at`. A game is started only through the initialize action, and a started game can
  never be put back to waiting. `started_at` and `finished_at` are read-only.
- The initialize action reports each game separately. A rejection or a database error such as
  `database is locked` is shown as an error message for that game, and the other selected games
  are still processed.

### Concurrency and SQLite

Initialization and player changes first re-read the game with `select_for_update()`.

- **PostgreSQL** (and other databases with row locks): the game row stays locked until commit, so
  a second attempt, or a player joining/leaving at the same moment, waits. It then sees the new
  state and is rejected.
- **SQLite** (used for development and tests) has no row locks, and Django ignores
  `select_for_update()` there. With SQLite's default deferred transactions, two attempts can both
  read `waiting`. One of them then fails with `OperationalError: database is locked` instead of a
  clean rejection. To handle this, the project sets `OPTIONS["transaction_mode"] = "IMMEDIATE"`
  (`config/settings.py`). Every transaction then takes SQLite's write lock at `BEGIN`, so concurrent
  initializations and player changes run one after another. The later one sees the committed state
  and is rejected with `invalid_status` or `invalid_player_count`.
- **SQLite limits**, which still apply:
  - The lock covers the whole database, not one game, so all writes are serialized. That is fine
    for development but does not scale like PostgreSQL.
  - A writer waits at most `OPTIONS["timeout"]` (20 s) and then fails with
    `database is locked`. Its transaction is rolled back and nothing is written.
  - `transaction_mode` is a connection setting, so **every** `transaction.atomic()` block in the
    project starts with `BEGIN IMMEDIATE` and takes the write lock, including blocks that only read
    (for example admin change views). Django has no way to apply it to a single block. This is
    acceptable for a development database. On PostgreSQL the option does not exist, and only the
    game row is locked.
  - Behaviour is not identical to PostgreSQL. Only the guarantees above are relied on.

`games/tests/test_initialization.py::ConcurrentInitializationTests` runs real parallel attempts in
threads, each with its own connection. For this the test database is a file
(`backend/test_db.sqlite3`, created and removed by the test runner, git-ignored) rather than
in-memory. Without `IMMEDIATE` these tests fail with `database is locked`.

### Tests

```bash
cd backend
python manage.py test                          # all milestones
python manage.py test games.tests.test_initialization
```
