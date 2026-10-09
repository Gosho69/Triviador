import random

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from territories.map import ADJACENCIES, TERRITORIES, validate_map
from territories.models import Capital, Territory
from territories.services import assign_capitals, build_game_map
from territories.validation import validate_game_map

from .models import Game, GamePlayer

PLAYERS_COUNT = 3


def initialize_game(game, *, rng=None, territories=TERRITORIES, adjacencies=ADJACENCIES):
    """Build the game's map, assign capitals and start it, all or nothing.

    The game row is re-read under `select_for_update`, so a stale instance or a concurrent
    attempt cannot initialize it twice (row locks need a database that supports them, see
    README). `rng` only needs `choice` and `sample`; tests pass a seeded `random.Random`.
    """
    with transaction.atomic():
        locked = Game.objects.select_for_update().get(pk=game.pk)
        _ensure_waiting(locked)

        players = list(locked.players.order_by("player_order"))
        if len(players) != PLAYERS_COUNT:
            raise ValidationError(
                "A game needs exactly %(count)d players to start; it has %(actual)d.",
                code="invalid_player_count",
                params={"count": PLAYERS_COUNT, "actual": len(players)},
            )

        if (
            Territory.objects.filter(game=locked).exists()
            or Capital.objects.filter(Q(player__game=locked) | Q(territory__game=locked)).exists()
        ):
            raise ValidationError(
                "The game already has territories or capitals and cannot be initialized again.",
                code="already_initialized",
            )

        try:
            validate_map(territories, adjacencies)
        except ValidationError as error:
            raise ValidationError(
                [ValidationError("The map definition is invalid.", code="invalid_map"), *error.error_list]
            ) from error

        territories_by_slug = build_game_map(locked, territories, adjacencies)
        assign_capitals(players, territories_by_slug, adjacencies, rng or random.SystemRandom())
        validate_game_map(locked, territories, adjacencies)

        locked.status = Game.IN_PROGRESS
        locked.started_at = timezone.now()
        locked.save(update_fields=["status", "started_at"])

    game.status, game.started_at = locked.status, locked.started_at
    return game


def add_player(game, user):
    """Join a waiting game; players are fixed once the game has started."""
    with transaction.atomic():
        locked = Game.objects.select_for_update().get(pk=game.pk)
        _ensure_waiting(locked)
        if locked.players.filter(user=user).exists():
            raise ValidationError(
                "%(user)s has already joined the game.", code="already_joined", params={"user": user}
            )
        if locked.players.count() >= PLAYERS_COUNT:
            raise ValidationError(
                "The game already has %(count)d players.", code="game_full", params={"count": PLAYERS_COUNT}
            )
        # Reuse the lowest free seat, so seats stay 1..PLAYERS_COUNT after someone leaves.
        taken = set(locked.players.values_list("player_order", flat=True))
        seat = min(set(range(1, PLAYERS_COUNT + 1)) - taken)
        return GamePlayer.objects.create(game=locked, user=user, player_order=seat)


def remove_player(player):
    """Leave a waiting game; players are fixed once the game has started. The host cancels instead."""
    with transaction.atomic():
        locked = Game.objects.select_for_update().get(pk=player.game_id)
        _ensure_waiting(locked)
        if player.user_id == locked.created_by_id:
            raise ValidationError(
                "The host cannot leave the game; cancel it instead.", code="host_cannot_leave"
            )
        player.delete()


def create_game(user):
    """Open a new waiting game with its creator in the first seat."""
    with transaction.atomic():
        game = Game.objects.create(created_by=user)
        add_player(game, user)
    return game


def cancel_game(game):
    """Close a waiting game for good; a started game cannot be cancelled this way."""
    with transaction.atomic():
        locked = Game.objects.select_for_update().get(pk=game.pk)
        _ensure_waiting(locked)
        locked.status = Game.CANCELLED
        locked.finished_at = timezone.now()
        locked.save(update_fields=["status", "finished_at"])
    game.status, game.finished_at = locked.status, locked.finished_at
    return game


def _ensure_waiting(game):
    if game.status != Game.WAITING:
        raise ValidationError(
            "Only a waiting game can be changed this way; this game is %(status)s.",
            code="invalid_status",
            params={"status": game.get_status_display().lower()},
        )
