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
| `games` | M3 | `Game`, `GamePlayer`, `Round`, `RoundAnswer` |
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

### Not in M4

Creating a game's territories, choosing capitals and starting the game are **M05 (game
initialization)**. Creating a `Game` in M4 creates no territories or capitals and does not change its
status.
