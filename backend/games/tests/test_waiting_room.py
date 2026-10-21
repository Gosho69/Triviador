import random

from django.contrib.auth import get_user_model
from django.test import TestCase

from games.models import Game, GamePlayer, WaitingRoomEntry
from games.waiting_room import form_game

User = get_user_model()


def wait(*names):
    users = [User.objects.create_user(username=name, email=f"{name}@example.com") for name in names]
    for user in users:
        WaitingRoomEntry.objects.create(user=user)
    return users


def waiting_users():
    return {entry.user for entry in WaitingRoomEntry.objects.all()}


class FormGameTests(TestCase):
    def test_five_waiting_creates_game_and_two_remain(self):
        waiting = wait("ana", "boris", "vera", "georgi", "maria")
        old_game = Game.objects.create(created_by=waiting[0], status=Game.FINISHED)
        GamePlayer.objects.create(game=old_game, user=waiting[0], player_order=1)

        form_game(rng=random.Random(7))

        game = Game.objects.get(status=Game.WAITING)
        players = list(game.players.all())
        chosen = {player.user for player in players}
        self.assertEqual(len(players), 3)
        self.assertEqual(len(chosen), 3)
        self.assertTrue(chosen <= set(waiting))
        self.assertEqual({player.color for player in players}, {"red", "blue", "green"})
        self.assertEqual({player.score for player in players}, {0})

        self.assertEqual(waiting_users(), set(waiting) - chosen)
        self.assertEqual(len(waiting_users()), 2)
        self.assertTrue(Game.objects.filter(pk=old_game.pk, status=Game.FINISHED).exists())

    def test_two_waiting_changes_nothing(self):
        waiting = wait("ana", "boris")

        self.assertIsNone(form_game())

        self.assertFalse(Game.objects.exists())
        self.assertFalse(GamePlayer.objects.exists())
        self.assertEqual(waiting_users(), set(waiting))
