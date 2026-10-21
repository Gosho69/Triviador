import random

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import Game, GamePlayer, WaitingRoomEntry
from .services import PLAYERS_COUNT

COLORS = [GamePlayer.RED, GamePlayer.BLUE, GamePlayer.GREEN]


def busy_players():
    return GamePlayer.objects.filter(game__status__in=[Game.WAITING, Game.IN_PROGRESS])


def eligible_entries():
    return WaitingRoomEntry.objects.exclude(user__in=busy_players().values("user"))


def join_waiting_room(user):
    if busy_players().filter(user=user).exists():
        raise ValidationError("You are already in a waiting or active game.", code="not_eligible")
    try:
        with transaction.atomic():
            WaitingRoomEntry.objects.create(user=user)
    except IntegrityError:
        raise ValidationError("You are already in the waiting room.", code="already_waiting") from None
    return form_game()


def leave_waiting_room(user):
    deleted, _ = WaitingRoomEntry.objects.filter(user=user).delete()
    return deleted > 0


def form_game(rng=None):
    rng = rng or random.SystemRandom()
    with transaction.atomic():
        entries = list(eligible_entries())
        if len(entries) < PLAYERS_COUNT:
            return None

        chosen = rng.sample(entries, PLAYERS_COUNT)
        colors = rng.sample(COLORS, PLAYERS_COUNT)
        game = Game.objects.create(created_by_id=chosen[0].user_id, status=Game.WAITING)
        GamePlayer.objects.bulk_create(
            GamePlayer(game=game, user_id=entry.user_id, player_order=order, color=color, score=0)
            for order, (entry, color) in enumerate(zip(chosen, colors), start=1)
        )
        WaitingRoomEntry.objects.filter(pk__in=[entry.pk for entry in chosen]).delete()
        return game
