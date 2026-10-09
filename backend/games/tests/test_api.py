from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import Profile
from games.models import Game, GamePlayer
from games.services import PLAYERS_COUNT, add_player, create_game, initialize_game
from territories.map import ADJACENCIES, TERRITORIES
from territories.models import Territory

User = get_user_model()

LIST_URL = reverse("games:list")


def url(name, game):
    return reverse(f"games:{name}", args=[game.pk])


def create_player(name, avatar_key="knight-1"):
    user = User.objects.create_user(username=name, email=f"{name}@example.com", password="Str0ng-pass-123")
    Profile.objects.create(user=user, nickname=name.title(), avatar_key=avatar_key)
    return user


class GameApiTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = create_player("host", "knight-2")
        cls.ana, cls.boris, cls.vera = (create_player(name) for name in ("ana", "boris", "vera"))

    def setUp(self):
        self.client.force_authenticate(self.host)

    def full_game(self):
        game = create_game(self.host)
        add_player(game, self.ana)
        add_player(game, self.boris)
        return game

    def assert_error(self, response, status_code, text):
        self.assertEqual(response.status_code, status_code)
        messages = [message for values in response.data["errors"].values() for message in values]
        self.assertTrue(any(text in message for message in messages), messages)


class GameListTests(GameApiTestCase):
    def test_lists_waiting_games_and_own_started_games_only(self):
        waiting = create_game(self.ana)
        mine = self.full_game()
        initialize_game(mine)
        others = create_game(self.boris)
        add_player(others, self.ana)
        add_player(others, self.vera)
        initialize_game(others)
        cancelled = create_game(self.vera)
        Game.objects.filter(pk=cancelled.pk).update(status=Game.CANCELLED)

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual([game["id"] for game in response.data], [waiting.pk, mine.pk])
        self.assertNotIn("board", response.data[0])

    def test_list_describes_players_and_your_role(self):
        game = create_game(self.ana)
        add_player(game, self.host)

        with self.assertNumQueries(2):  # games, players with their profiles
            data = self.client.get(LIST_URL).data[0]

        self.assertFalse(data["is_host"])
        self.assertTrue(data["is_member"])
        self.assertEqual(data["seats"], PLAYERS_COUNT)
        self.assertEqual(
            [(p["seat"], p["nickname"], p["is_you"], p["is_host"]) for p in data["players"]],
            [(1, "Ana", False, True), (2, "Host", True, False)],
        )
        self.assertEqual(data["players"][1]["avatar_key"], "knight-2")

    def test_anonymous_users_are_rejected(self):
        self.client.force_authenticate(None)

        response = self.client.get(LIST_URL)

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class CreateAndDetailTests(GameApiTestCase):
    def test_creating_a_game_seats_the_creator(self):
        response = self.client.post(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Game.WAITING)
        self.assertTrue(response.data["is_host"])
        self.assertEqual([player["seat"] for player in response.data["players"]], [1])
        self.assertIsNone(response.data["board"])

    def test_waiting_game_detail_skips_the_board_queries(self):
        game = create_game(self.host)

        with self.assertNumQueries(2):  # game, players with their profiles
            data = self.client.get(url("detail", game)).data

        self.assertIsNone(data["board"])

    def test_player_without_profile_is_shown_by_username(self):
        admin = User.objects.create_superuser(username="root", email="root@example.com", password="Str0ng-pass-123")
        game = create_game(admin)

        player = self.client.get(url("detail", game)).data["players"][0]

        self.assertEqual((player["nickname"], player["avatar_key"]), ("root", None))

    def test_started_game_has_the_board_in_map_order(self):
        game = self.full_game()
        initialize_game(game)

        with self.assertNumQueries(4):  # game, players, territories with owners and capitals, borders
            data = self.client.get(url("detail", game)).data

        territories = data["board"]["territories"]
        self.assertEqual([(t["slug"], t["name"]) for t in territories], list(TERRITORIES))
        self.assertEqual(sum(len(t["neighbors"]) for t in territories), 2 * len(ADJACENCIES))
        capitals = [t for t in territories if t["capital"]]
        self.assertCountEqual([t["owner_seat"] for t in capitals], [1, 2, 3])
        self.assertTrue(all(t["capital"] == {"health": 3, "max_health": 3} for t in capitals))
        self.assertEqual(sum(t["owner_seat"] is None for t in territories), len(TERRITORIES) - PLAYERS_COUNT)

    def test_started_game_is_hidden_from_non_players(self):
        game = self.full_game()
        initialize_game(game)
        self.client.force_authenticate(self.vera)

        self.assertEqual(self.client.get(url("detail", game)).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(url("join", game)).status_code, status.HTTP_404_NOT_FOUND)


class JoinAndLeaveTests(GameApiTestCase):
    def test_join_takes_the_next_free_seat(self):
        game = create_game(self.ana)

        response = self.client.post(url("join", game))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_member"])
        self.assertEqual([player["seat"] for player in response.data["players"]], [1, 2])

    def test_seat_freed_by_a_leaving_player_is_reused(self):
        game = self.full_game()
        self.client.force_authenticate(self.ana)
        self.client.post(url("leave", game))
        self.client.force_authenticate(self.vera)

        response = self.client.post(url("join", game))

        self.assertEqual(sorted(player["seat"] for player in response.data["players"]), [1, 2, 3])

    def test_join_rejections_use_the_error_envelope(self):
        game = self.full_game()
        self.assert_error(self.client.post(url("join", game)), status.HTTP_400_BAD_REQUEST, "already joined")
        self.client.force_authenticate(self.vera)
        self.assert_error(self.client.post(url("join", game)), status.HTTP_400_BAD_REQUEST, "already has 3 players")

    def test_player_can_leave_but_host_cannot(self):
        game = self.full_game()
        self.assert_error(self.client.post(url("leave", game)), status.HTTP_400_BAD_REQUEST, "cancel it instead")

        self.client.force_authenticate(self.ana)
        self.assertEqual(self.client.post(url("leave", game)).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(game.players.filter(user=self.ana).exists())
        self.assert_error(self.client.post(url("leave", game)), status.HTTP_400_BAD_REQUEST, "not in this game")

    def test_players_are_fixed_after_the_start(self):
        game = self.full_game()
        initialize_game(game)
        self.client.force_authenticate(self.ana)

        self.assert_error(self.client.post(url("leave", game)), status.HTTP_400_BAD_REQUEST, "waiting game")
        self.assertEqual(game.players.count(), PLAYERS_COUNT)


class StartAndCancelTests(GameApiTestCase):
    def test_host_starts_a_full_game(self):
        game = self.full_game()

        response = self.client.post(url("start", game))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Game.IN_PROGRESS)
        self.assertEqual(len(response.data["board"]["territories"]), len(TERRITORIES))

    def test_only_the_host_can_start_or_cancel(self):
        game = self.full_game()
        self.client.force_authenticate(self.ana)

        for action in ("start", "cancel"):
            with self.subTest(action):
                self.assert_error(self.client.post(url(action, game)), status.HTTP_403_FORBIDDEN, "Only the host")
        game.refresh_from_db()
        self.assertEqual(game.status, Game.WAITING)

    def test_start_needs_three_players(self):
        game = create_game(self.host)
        add_player(game, self.ana)

        self.assert_error(self.client.post(url("start", game)), status.HTTP_400_BAD_REQUEST, "exactly 3 players")
        self.assertFalse(Territory.objects.filter(game=game).exists())

    def test_host_cancels_a_waiting_game(self):
        game = create_game(self.host)
        add_player(game, self.ana)

        self.assertEqual(self.client.post(url("cancel", game)).status_code, status.HTTP_204_NO_CONTENT)

        game.refresh_from_db()
        self.assertEqual(game.status, Game.CANCELLED)
        self.assertIsNotNone(game.finished_at)
        self.assertNotIn(game.pk, [g["id"] for g in self.client.get(LIST_URL).data])
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.client.get(url("detail", game)).data["status"], Game.CANCELLED)

    def test_started_game_cannot_be_cancelled(self):
        game = self.full_game()
        initialize_game(game)

        self.assert_error(self.client.post(url("cancel", game)), status.HTTP_400_BAD_REQUEST, "waiting game")

    def test_csrf_is_enforced_for_session_users(self):
        game = create_game(self.ana)
        client = APIClient(enforce_csrf_checks=True)
        client.login(username="host", password="Str0ng-pass-123")

        response = client.post(url("join", game))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(GamePlayer.objects.filter(game=game, user=self.host).exists())
