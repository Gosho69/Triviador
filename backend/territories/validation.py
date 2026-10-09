from django.core.exceptions import ValidationError
from django.db.models import Q

from .map import ADJACENCIES, TERRITORIES
from .models import Adjacency, Territory


def validate_game_map(game, territories=TERRITORIES, adjacencies=ADJACENCIES):
    """Check that a game's territory records match the project map. Read-only."""
    errors = []

    rows = Territory.objects.filter(game=game).values_list("pk", "slug", "name")
    slugs_by_pk = {pk: slug for pk, slug, _ in rows}
    expected_territories = set(territories)
    actual_territories = {(slug, name) for _, slug, name in rows}
    if actual_territories != expected_territories:
        errors.append(
            ValidationError(
                "The game's territories differ from the map. Missing: %(missing)s. Unexpected: %(unexpected)s.",
                code="territory_mismatch",
                params={
                    "missing": _format_territories(expected_territories - actual_territories),
                    "unexpected": _format_territories(actual_territories - expected_territories),
                },
            )
        )

    borders = Adjacency.objects.filter(
        Q(from_territory__game=game) | Q(to_territory__game=game)
    ).values_list("from_territory_id", "to_territory_id")
    directed = set()
    has_cross_game_border = False
    for from_id, to_id in borders:
        if from_id in slugs_by_pk and to_id in slugs_by_pk:
            directed.add((slugs_by_pk[from_id], slugs_by_pk[to_id]))
        else:
            has_cross_game_border = True
    if has_cross_game_border:
        errors.append(
            ValidationError("The game has borders with another game's territories.", code="cross_game_adjacency")
        )

    if any((second, first) not in directed for first, second in directed):
        errors.append(ValidationError("Every border must be stored in both directions.", code="asymmetric_adjacency"))

    expected_borders = {frozenset(pair) for pair in adjacencies}
    actual_borders = {frozenset(pair) for pair in directed}
    if actual_borders != expected_borders:
        errors.append(
            ValidationError(
                "The game's borders differ from the map. Missing: %(missing)s. Unexpected: %(unexpected)s.",
                code="adjacency_mismatch",
                params={
                    "missing": _format_borders(expected_borders - actual_borders),
                    "unexpected": _format_borders(actual_borders - expected_borders),
                },
            )
        )

    if errors:
        raise ValidationError(errors)


def _format_territories(territories):
    return ", ".join(f"{slug} ({name})" for slug, name in sorted(territories)) or "none"


def _format_borders(borders):
    return ", ".join(sorted("–".join(sorted(border)) for border in borders)) or "none"
