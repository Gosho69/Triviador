from django.core.exceptions import ValidationError

from .map import ADJACENCIES, CAPITALS_COUNT, TERRITORIES, build_neighbor_map, capital_groups
from .models import Adjacency, Capital, Territory


def build_game_map(game, territories=TERRITORIES, adjacencies=ADJACENCIES):
    """Create a game's territories and borders from a map definition. Returns them by slug."""
    Territory.objects.bulk_create(Territory(game=game, slug=slug, name=name) for slug, name in territories)
    territories_by_slug = {territory.slug: territory for territory in Territory.objects.filter(game=game)}
    Adjacency.objects.bulk_create(
        Adjacency(from_territory=territories_by_slug[start], to_territory=territories_by_slug[end])
        for first, second in adjacencies
        for start, end in ((first, second), (second, first))
    )
    return territories_by_slug


def assign_capitals(players, territories_by_slug, adjacencies, rng):
    """Give each player a random capital; the capitals are pairwise non-adjacent.

    A group is chosen uniformly and then shuffled, so every ordered assignment is equally
    likely and the result does not depend on the order of players or territories.
    """
    candidates = list(capital_groups(build_neighbor_map(territories_by_slug, adjacencies)))
    if not candidates:
        raise ValidationError(
            "No %(count)d pairwise non-adjacent territories are available for the capitals.",
            code="no_capital_assignment",
            params={"count": CAPITALS_COUNT},
        )

    slugs = rng.sample(rng.choice(candidates), CAPITALS_COUNT)
    capitals = []
    for player, slug in zip(players, slugs, strict=True):
        territory = territories_by_slug[slug]
        territory.owner = player
        territory.save(update_fields=["owner"])
        capitals.append(Capital.objects.create(territory=territory, player=player))
    return capitals
