"""The project map: one fixed set of territories and borders shared by every game.

Each game gets its own Territory records built from this definition (M05).
"""

from collections import deque
from itertools import combinations

from django.core.exceptions import ValidationError

MAP_SIZE_MIN = 9
MAP_SIZE_MAX = 21
MAP_SIZE_STEP = 3
MIN_NEIGHBORS = 2
CAPITALS_COUNT = 3

TERRITORIES = (
    # North
    ("skali", "Скали"),
    ("dunaviya", "Дунавия"),
    ("zhitno-pole", "Житно поле"),
    ("leventa", "Левента"),
    ("pelikania", "Пеликания"),
    ("kaliakra", "Калиакра"),
    # Middle
    ("sredets", "Средец"),
    ("balkania", "Балкания"),
    ("rozova-dolina", "Розова долина"),
    ("madara", "Мадара"),
    ("zlaten-grozd", "Златен грозд"),
    ("slanchevo", "Слънчево"),
    # South
    ("pirina", "Пирина"),
    ("ezera", "Езера"),
    ("kukeri", "Кукери"),
    ("chuden-kray", "Чуден край"),
    ("karakachan", "Каракачан"),
    ("tsarevo", "Царево"),
)

ADJACENCIES = (
    # North row
    ("skali", "dunaviya"),
    ("dunaviya", "zhitno-pole"),
    ("zhitno-pole", "leventa"),
    ("leventa", "pelikania"),
    ("pelikania", "kaliakra"),
    # Middle row
    ("sredets", "balkania"),
    ("balkania", "rozova-dolina"),
    ("rozova-dolina", "madara"),
    ("madara", "zlaten-grozd"),
    ("zlaten-grozd", "slanchevo"),
    # South row
    ("pirina", "ezera"),
    ("ezera", "kukeri"),
    ("kukeri", "chuden-kray"),
    ("chuden-kray", "karakachan"),
    ("karakachan", "tsarevo"),
    # North to middle
    ("skali", "sredets"),
    ("dunaviya", "balkania"),
    ("zhitno-pole", "rozova-dolina"),
    ("leventa", "madara"),
    ("pelikania", "zlaten-grozd"),
    ("kaliakra", "slanchevo"),
    # Middle to south
    ("sredets", "pirina"),
    ("balkania", "ezera"),
    ("rozova-dolina", "kukeri"),
    ("madara", "chuden-kray"),
    ("zlaten-grozd", "karakachan"),
    ("slanchevo", "tsarevo"),
    # Diagonal borders
    ("dunaviya", "rozova-dolina"),
    ("leventa", "zlaten-grozd"),
    ("balkania", "kukeri"),
    ("madara", "karakachan"),
)


def build_neighbor_map(slugs, adjacencies):
    """Map every slug to the set of its neighbours, ignoring edges to unknown slugs."""
    neighbors = {slug: set() for slug in slugs}
    for first, second in adjacencies:
        if first in neighbors and second in neighbors and first != second:
            neighbors[first].add(second)
            neighbors[second].add(first)
    return neighbors


def is_connected(neighbor_map):
    if not neighbor_map:
        return False
    start = next(iter(neighbor_map))
    seen = {start}
    queue = deque([start])
    while queue:
        for neighbor in neighbor_map[queue.popleft()]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len(seen) == len(neighbor_map)


def capital_groups(neighbor_map):
    """Yield every group of CAPITALS_COUNT pairwise non-adjacent territories, as sorted slug tuples."""
    for group in combinations(sorted(neighbor_map), CAPITALS_COUNT):
        if all(second not in neighbor_map[first] for first, second in combinations(group, 2)):
            yield group


def has_capital_triple(neighbor_map):
    """Whether some CAPITALS_COUNT territories exist that are pairwise non-adjacent."""
    return next(capital_groups(neighbor_map), None) is not None


def validate_map(territories, adjacencies):
    """Validate a map definition without touching the database.

    `territories` is a sequence of (slug, name) pairs and `adjacencies` a sequence of
    (slug, slug) pairs, each border listed once.
    """
    errors = []
    slugs = [slug for slug, _ in territories]
    names = [name for _, name in territories]

    size = len(territories)
    if not (MAP_SIZE_MIN <= size <= MAP_SIZE_MAX and size % MAP_SIZE_STEP == 0):
        errors.append(
            ValidationError(
                "A map must have between %(min)d and %(max)d territories, in multiples of %(step)d; got %(size)d.",
                code="invalid_size",
                params={"min": MAP_SIZE_MIN, "max": MAP_SIZE_MAX, "step": MAP_SIZE_STEP, "size": size},
            )
        )
    if len(set(slugs)) != len(slugs):
        errors.append(ValidationError("Territory slugs must be unique.", code="duplicate_slug"))
    if len(set(names)) != len(names):
        errors.append(ValidationError("Territory names must be unique.", code="duplicate_name"))

    known = set(slugs)
    seen_borders = set()
    for first, second in adjacencies:
        if first not in known or second not in known:
            errors.append(
                ValidationError(
                    "Border %(first)s–%(second)s references an unknown territory.",
                    code="unknown_territory",
                    params={"first": first, "second": second},
                )
            )
        elif first == second:
            errors.append(
                ValidationError(
                    "Territory %(slug)s cannot border itself.",
                    code="self_adjacency",
                    params={"slug": first},
                )
            )
        elif frozenset((first, second)) in seen_borders:
            errors.append(
                ValidationError(
                    "Border %(first)s–%(second)s is listed more than once.",
                    code="duplicate_adjacency",
                    params={"first": first, "second": second},
                )
            )
        seen_borders.add(frozenset((first, second)))

    neighbor_map = build_neighbor_map(known, adjacencies)
    isolated = sorted(slug for slug, neighbors in neighbor_map.items() if len(neighbors) < MIN_NEIGHBORS)
    if isolated:
        errors.append(
            ValidationError(
                "Every territory needs at least %(min)d neighbours: %(slugs)s.",
                code="too_few_neighbors",
                params={"min": MIN_NEIGHBORS, "slugs": ", ".join(isolated)},
            )
        )
    if not is_connected(neighbor_map):
        errors.append(
            ValidationError("Every territory must be reachable from every other.", code="disconnected")
        )
    if not has_capital_triple(neighbor_map):
        errors.append(
            ValidationError(
                "The map needs %(count)d pairwise non-adjacent territories for the starting capitals.",
                code="no_capital_triple",
                params={"count": CAPITALS_COUNT},
            )
        )

    if errors:
        raise ValidationError(errors)
