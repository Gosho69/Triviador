import random
from unittest import mock

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from games.admin import GameAdminForm, GamePlayerInline
from games.models import Game, GamePlayer
from games.services import PLAYERS_COUNT, initialize_game

User = get_user_model()


class GameAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="Str0ng-pass-123"
        )
        cls.users = [
            User.objects.create_user(username=name, email=f"{name}@example.com", password="Str0ng-pass-123")
            for name in ("ana", "boris", "vera", "galya")
        ]

    def setUp(self):
        self.game = Game.objects.create(created_by=self.admin)
        for order, user in enumerate(self.users[:PLAYERS_COUNT], start=1):
            GamePlayer.objects.create(game=self.game, user=user, player_order=order)
        self.request = RequestFactory().post("/")
        self.request.user = self.admin

    def player_formset(self, game, new_users=(), deleted=()):
        """Bind the players inline exactly as the admin change form would post it."""
        players = list(GamePlayer.objects.filter(game=game).order_by("player_order"))
        data = {
            "players-TOTAL_FORMS": len(players) + len(new_users),
            "players-INITIAL_FORMS": len(players),
            "players-MIN_NUM_FORMS": 0,
            "players-MAX_NUM_FORMS": 1000,
        }
        rows = [(player.pk, player.user_id, player.player_order) for player in players]
        rows += [("", user.pk, len(players) + index) for index, user in enumerate(new_users, start=1)]
        for index, (pk, user_id, order) in enumerate(rows):
            data.update({
                f"players-{index}-id": pk,
                f"players-{index}-game": game.pk,
                f"players-{index}-user": user_id,
                f"players-{index}-player_order": order,
                f"players-{index}-score": 0,
                f"players-{index}-is_active": "on",
            })
            if pk and pk in deleted:
                data[f"players-{index}-DELETE"] = "on"

        formset_class = GamePlayerInline(Game, site).get_formset(self.request, game)
        return formset_class(data, instance=game, prefix="players")

    def post_change_form(self, game, **fields):
        data = {
            "created_by": game.created_by_id,
            "status": game.status,
            "players-TOTAL_FORMS": 0,
            "players-INITIAL_FORMS": 0,
            "players-MIN_NUM_FORMS": 0,
            "players-MAX_NUM_FORMS": 1000,
            "_save": "Save",
            **fields,
        }
        return self.client.post(reverse("admin:games_game_change", args=[game.pk]), data)


class PlayerInlineTests(GameAdminTestCase):
    def test_waiting_game_players_can_be_edited(self):
        game = Game.objects.create(created_by=self.admin)
        formset = self.player_formset(game, new_users=self.users[:PLAYERS_COUNT])

        self.assertTrue(formset.is_valid(), formset.non_form_errors())
        formset.save()
        self.assertEqual(game.players.count(), PLAYERS_COUNT)

    def test_fourth_player_is_rejected_on_the_server(self):
        formset = self.player_formset(self.game, new_users=self.users[3:])

        self.assertFalse(formset.is_valid())
        self.assertIn("at most 3 players", str(formset.non_form_errors()))
        self.assertEqual(self.game.players.count(), PLAYERS_COUNT)

    def test_replacing_a_player_stays_within_the_limit(self):
        removed = self.game.players.last()

        formset = self.player_formset(self.game, new_users=self.users[3:], deleted=[removed.pk])

        self.assertTrue(formset.is_valid(), formset.non_form_errors())

    def test_form_opened_before_the_start_cannot_change_players_afterwards(self):
        stale_game = Game.objects.get(pk=self.game.pk)
        player = self.game.players.first()
        formsets = {
            "delete": lambda: self.player_formset(stale_game, deleted=[player.pk]),
            "add": lambda: self.player_formset(stale_game, new_users=self.users[3:]),
        }
        initialize_game(self.game, rng=random.Random(1))

        for label, build in formsets.items():
            with self.subTest(label):
                formset = build()
                self.assertFalse(formset.is_valid())
                self.assertIn("after the game has started", str(formset.non_form_errors()))
        self.assertEqual(self.game.players.count(), PLAYERS_COUNT)

    def test_unchanged_players_of_a_started_game_still_validate(self):
        initialize_game(self.game, rng=random.Random(1))

        self.assertTrue(self.player_formset(self.game).is_valid())


class GameStatusAdminTests(GameAdminTestCase):
    def status_errors(self, game, status):
        form = GameAdminForm(data={"created_by": game.created_by_id, "status": status}, instance=game)
        form.is_valid()
        return form.errors.get("status")

    def test_game_cannot_be_started_or_reopened_by_editing_its_status(self):
        self.assertTrue(self.status_errors(self.game, Game.IN_PROGRESS))

        initialize_game(self.game, rng=random.Random(1))
        self.assertTrue(self.status_errors(self.game, Game.WAITING))

    def test_new_game_must_start_as_waiting(self):
        self.assertTrue(self.status_errors(Game(created_by=self.admin), Game.IN_PROGRESS))
        self.assertIsNone(self.status_errors(Game(created_by=self.admin), Game.WAITING))

    def test_game_can_be_finished_or_cancelled_and_gets_finished_at(self):
        self.client.force_login(self.admin)
        initialize_game(self.game, rng=random.Random(1))
        waiting = Game.objects.create(created_by=self.admin)

        for game, status in ((self.game, Game.FINISHED), (waiting, Game.CANCELLED)):
            with self.subTest(status=status):
                response = self.post_change_form(game, status=status)

                self.assertEqual(response.status_code, 302)
                game.refresh_from_db()
                self.assertEqual(game.status, status)
                self.assertIsNotNone(game.finished_at)

    def test_rejected_status_change_is_not_saved(self):
        self.client.force_login(self.admin)

        response = self.post_change_form(self.game, status=Game.IN_PROGRESS)

        self.assertEqual(response.status_code, 200)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.WAITING)
        self.assertIsNone(self.game.finished_at)


class InitializeActionTests(GameAdminTestCase):
    def test_database_error_is_reported_and_other_games_continue(self):
        self.client.force_login(self.admin)
        second = Game.objects.create(created_by=self.admin)
        for order, user in enumerate(self.users[1:], start=1):
            GamePlayer.objects.create(game=second, user=user, player_order=order)

        def locked_for_first_game(game):
            if game.pk == self.game.pk:
                raise OperationalError("database is locked")
            return initialize_game(game, rng=random.Random(1))

        with mock.patch("games.admin.initialize_game", side_effect=locked_for_first_game):
            response = self.client.post(
                reverse("admin:games_game_changelist"),
                {"action": "initialize_games", "_selected_action": [self.game.pk, second.pk]},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in response.context["messages"]]
        self.assertTrue(any("database is locked" in message for message in messages))
        self.assertTrue(any(f"#{second.pk}" in message and "initialized" in message for message in messages))
        self.game.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.game.status, Game.WAITING)
        self.assertEqual(second.status, Game.IN_PROGRESS)
