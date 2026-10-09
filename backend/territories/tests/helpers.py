from territories.map import ADJACENCIES, TERRITORIES
from territories.models import Territory


def create_game_map(game):
    """Build a game's territories from the project map. Test setup only; real initialization is M05."""
    territories = {
        slug: Territory.objects.create(game=game, slug=slug, name=name) for slug, name in TERRITORIES
    }
    for first, second in ADJACENCIES:
        territories[first].neighbors.add(territories[second])
    return territories
