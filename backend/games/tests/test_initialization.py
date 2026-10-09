import random
import threading
import time
from io import StringIO
from itertools import combinations
from unittest import mock

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse

from games.admin import GamePlayerInline
from games.models import Game, GamePlayer, Round
from games.services import PLAYERS_COUNT, add_player, initialize_game, remove_player
from questions.models import Category, ChoiceQuestion
from territories.map import ADJACENCIES, TERRITORIES, build_neighbor_map, capital_groups
from territories.models import Adjacency, Capital, Territory
from territories.services import build_game_map
from territories.validation import validate_game_map

User = get_user_model()

MAP_SIZE = len(TERRITORIES)
NEIGHBORS = build_neighbor_map([slug for slug, _ in TERRITORIES], ADJACENCIES)


def create_users(*usernames):
    return [
        User.objects.create_user(username=name, email=f"{name}@example.com", password="Str0ng-pass-123")
        for name in usernames
    ]


def create_waiting_game(host, users):
    game = Game.objects.create(created_by=host)
    for order, user in enumerate(users, start=1):
        GamePlayer.objects.create(game=game, user=user, player_order=order)
    return game


def error_codes(error):
    return [item.code for item in error.error_list]


class FixedRandom:
    """Stand-in for `random.Random` that makes the capital choice explicit."""

    def __init__(self, group_index, reverse=False):
        self.group_index = group_index
        self.reverse = reverse

    def choice(self, candidates):
        return candidates[self.group_index]

    def sample(self, population, k):
        ordered = list(population)[::-1] if self.reverse else list(population)
        return ordered[:k]


class InitializationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host, *cls.users = create_users("host", "ana", "boris", "vera", "galya")
        cls.trio = cls.users[:PLAYERS_COUNT]

    def setUp(self):
        self.game = create_waiting_game(self.host, self.trio)

    def initialize(self, game=None, seed=1, **kwargs):
        return initialize_game(game or self.game, rng=random.Random(seed), **kwargs)

    def assert_rejected(self, code, game=None, **kwargs):
        with self.assertRaises(ValidationError) as context:
            self.initialize(game, **kwargs)
        self.assertIn(code, error_codes(context.exception))
        return context.exception

    def assert_untouched(self, game=None):
        game = game or self.game
        game.refresh_from_db()
        self.assertEqual(game.status, Game.WAITING)
        self.assertIsNone(game.started_at)
        self.assertFalse(Territory.objects.filter(game=game).exists())
        self.assertFalse(Adjacency.objects.filter(from_territory__game=game).exists())
        self.assertFalse(Capital.objects.filter(player__game=game).exists())

    def snapshot(self, game=None):
        game = game or self.game
        return (
            list(Territory.objects.filter(game=game).values_list("pk", "slug", "name", "owner_id", "score")),
            list(Adjacency.objects.filter(from_territory__game=game).values_list("pk", "from_territory", "to_territory")),
            list(Capital.objects.filter(player__game=game).values_list("pk", "player", "territory", "health")),
        )


class SuccessfulInitializationTests(InitializationTestCase):
    def test_waiting_game_with_three_players_gets_full_initial_state(self):
        returned = self.initialize()

        self.assertIs(returned, self.game)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.IN_PROGRESS)
        self.assertIsNotNone(self.game.started_at)

        territories = Territory.objects.filter(game=self.game)
        self.assertEqual(territories.count(), MAP_SIZE)
        self.assertFalse(territories.exclude(score=0).exists())
        self.assertEqual(territories.filter(owner=None).count(), MAP_SIZE - PLAYERS_COUNT)

        capitals = Capital.objects.filter(player__game=self.game).select_related("territory")
        self.assertEqual(capitals.count(), PLAYERS_COUNT)
        self.assertCountEqual([capital.player.user for capital in capitals], self.trio)
        for capital in capitals:
            self.assertEqual(capital.health, Capital.MAX_HEALTH)
            self.assertEqual(capital.territory.game_id, self.game.pk)
            self.assertEqual(capital.territory.owner_id, capital.player_id)
            self.assertEqual(list(capital.player.territories.all()), [capital.territory])

    def test_map_matches_the_project_definition(self):
        self.initialize()

        validate_game_map(self.game)
        self.assertCountEqual(
            Territory.objects.filter(game=self.game).values_list("slug", "name"), TERRITORIES
        )
        self.assertEqual(Adjacency.objects.filter(from_territory__game=self.game).count(), 2 * len(ADJACENCIES))
        self.assertFalse(Adjacency.objects.filter(from_territory__game=self.game).exclude(to_territory__game=self.game).exists())

    def test_capitals_are_pairwise_non_adjacent(self):
        for seed in range(25):
            with self.subTest(seed=seed):
                game = create_waiting_game(self.host, self.trio)
                self.initialize(game, seed=seed)

                capitals = list(Capital.objects.filter(player__game=game).select_related("territory"))
                for first, second in combinations(capitals, 2):
                    self.assertNotIn(second.territory, first.territory.neighbors.all())
                    self.assertNotIn(second.territory.slug, NEIGHBORS[first.territory.slug])

    def test_capital_choice_is_controlled_by_the_injected_random_source(self):
        candidates = list(capital_groups(NEIGHBORS))
        group = candidates[-1]

        initialize_game(self.game, rng=FixedRandom(-1, reverse=True))

        players = self.game.players.order_by("player_order")
        self.assertEqual(
            [Capital.for_player(player).territory.slug for player in players], list(reversed(group))
        )

    def test_same_seed_gives_same_capitals(self):
        other = create_waiting_game(self.host, self.trio)

        self.initialize(seed=7)
        self.initialize(other, seed=7)

        def capitals(game):
            return [
                Capital.for_player(player).territory.slug for player in game.players.order_by("player_order")
            ]

        self.assertEqual(capitals(self.game), capitals(other))

    def test_default_random_source_is_used_without_rng(self):
        initialize_game(self.game)

        self.assertEqual(Capital.objects.filter(player__game=self.game).count(), PLAYERS_COUNT)

    def test_creating_a_game_does_not_start_it(self):
        game = create_waiting_game(self.host, self.trio)

        self.assert_untouched(game)


class RejectedInitializationTests(InitializationTestCase):
    def test_player_count_other_than_three_is_rejected(self):
        cases = {
            "no players": [],
            "two players": self.users[:2],
            "four players": self.users[:4],
        }
        for label, users in cases.items():
            with self.subTest(label):
                game = create_waiting_game(self.host, users)

                self.assert_rejected("invalid_player_count", game)
                self.assert_untouched(game)

    def test_game_that_is_not_waiting_is_rejected(self):
        for status in (Game.IN_PROGRESS, Game.FINISHED, Game.CANCELLED):
            with self.subTest(status=status):
                game = create_waiting_game(self.host, self.trio)
                Game.objects.filter(pk=game.pk).update(status=status)
                game.refresh_from_db()

                self.assert_rejected("invalid_status", game)
                self.assertFalse(Territory.objects.filter(game=game).exists())
                game.refresh_from_db()
                self.assertEqual(game.status, status)

    def test_stale_waiting_instance_is_checked_against_the_database(self):
        Game.objects.filter(pk=self.game.pk).update(status=Game.IN_PROGRESS)

        self.assert_rejected("invalid_status")
        self.assertFalse(Territory.objects.filter(game=self.game).exists())

    def test_invalid_map_definition_is_rejected(self):
        too_small = TERRITORIES[:10]
        known = {slug for slug, _ in too_small}
        cases = {
            "invalid size": (too_small, [pair for pair in ADJACENCIES if set(pair) <= known], "invalid_size"),
            "no capital triple": (TERRITORIES[:9], list(combinations([s for s, _ in TERRITORIES[:9]], 2)), "no_capital_triple"),
        }
        for label, (territories, adjacencies, code) in cases.items():
            with self.subTest(label):
                error = self.assert_rejected("invalid_map", territories=territories, adjacencies=adjacencies)
                self.assertIn(code, error_codes(error))
                self.assert_untouched()

    def test_impossible_capital_assignment_leaves_no_records(self):
        with mock.patch("territories.services.capital_groups", return_value=iter(())):
            self.assert_rejected("no_capital_assignment")

        self.assert_untouched()

    def test_failure_during_the_operation_rolls_everything_back(self):
        with mock.patch("games.services.validate_game_map", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.initialize()

        self.assert_untouched()

    def test_failure_while_creating_capitals_rolls_everything_back(self):
        create = Capital.objects.create
        calls = []

        def fail_on_last(**fields):
            calls.append(fields)
            if len(calls) == PLAYERS_COUNT:
                raise RuntimeError("boom")
            return create(**fields)

        with mock.patch.object(Capital.objects, "create", side_effect=fail_on_last):
            with self.assertRaises(RuntimeError):
                self.initialize()

        self.assert_untouched()
        self.assertFalse(Territory.objects.exclude(owner=None).exists())

    def test_second_initialization_is_rejected_without_changes(self):
        self.initialize()
        before = self.snapshot()

        self.assert_rejected("invalid_status", seed=99)

        self.assertEqual(self.snapshot(), before)

    def test_existing_map_is_never_redone_even_if_status_is_reset(self):
        self.initialize()
        before = self.snapshot()
        Game.objects.filter(pk=self.game.pk).update(status=Game.WAITING)

        self.assert_rejected("already_initialized", seed=99)

        self.assertEqual(self.snapshot(), before)

    def test_partial_previous_state_is_rejected_and_not_repaired(self):
        Territory.objects.create(game=self.game, slug="skali", name="Скали")
        before = self.snapshot()

        self.assert_rejected("already_initialized")

        self.assertEqual(self.snapshot(), before)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.WAITING)

    def test_map_without_capitals_is_rejected_and_not_completed(self):
        build_game_map(self.game)
        before = self.snapshot()

        self.assert_rejected("already_initialized")

        self.assertEqual(self.snapshot(), before)
        self.assertFalse(Capital.objects.exists())


class InitializationIsolationTests(InitializationTestCase):
    def test_games_share_map_structure_but_not_records(self):
        other = create_waiting_game(self.host, self.users[1:4])
        self.initialize(seed=1)
        self.initialize(other, seed=2)

        def structure(game):
            slugs = dict(Territory.objects.filter(game=game).values_list("pk", "slug"))
            borders = {
                frozenset((slugs[a], slugs[b]))
                for a, b in Adjacency.objects.filter(from_territory__game=game).values_list("from_territory", "to_territory")
            }
            return set(slugs.values()), borders

        self.assertEqual(structure(self.game), structure(other))
        own_pks = set(self.game.territories.values_list("pk", flat=True))
        self.assertTrue(own_pks.isdisjoint(other.territories.values_list("pk", flat=True)))

        other_before = self.snapshot(other)
        territory = self.game.territories.get(slug="sredets")
        territory.score = 5
        territory.owner = self.game.players.first()
        territory.save()
        Capital.objects.filter(player__game=self.game).update(health=1)

        self.assertEqual(self.snapshot(other), other_before)

    def test_definition_player_scores_and_rounds_are_not_changed(self):
        category = Category.objects.create(name="История")
        question = ChoiceQuestion.objects.create(category=category, text="Кой хан основава Дунавска България?")
        round_ = Round.objects.create(game=self.game, number=1, question_type=Round.CHOICE, choice_question=question)
        GamePlayer.objects.filter(game=self.game).update(score=4)
        definition = (tuple(TERRITORIES), tuple(ADJACENCIES))
        round_before = Round.objects.filter(pk=round_.pk).values().get()

        self.initialize()

        self.assertEqual((tuple(TERRITORIES), tuple(ADJACENCIES)), definition)
        self.assertEqual(list(self.game.players.values_list("score", flat=True)), [4, 4, 4])
        self.assertEqual(Round.objects.filter(game=self.game).count(), 1)
        self.assertEqual(Round.objects.filter(pk=round_.pk).values().get(), round_before)


class PlayerChangeTests(InitializationTestCase):
    def test_players_can_join_and_leave_a_waiting_game(self):
        game = create_waiting_game(self.host, self.users[:2])

        joined = add_player(game, self.users[2])
        self.assertEqual(joined.player_order, 3)

        remove_player(joined)
        self.assertEqual(game.players.count(), 2)

    def test_same_user_cannot_join_twice(self):
        game = create_waiting_game(self.host, self.users[:2])

        with self.assertRaises(ValidationError) as context:
            add_player(game, self.users[0])

        self.assertIn("already_joined", error_codes(context.exception))
        self.assertEqual(game.players.count(), 2)

    def test_waiting_game_cannot_get_a_fourth_player(self):
        with self.assertRaises(ValidationError) as context:
            add_player(self.game, self.users[3])

        self.assertIn("game_full", error_codes(context.exception))
        self.assertEqual(self.game.players.count(), PLAYERS_COUNT)

    def test_players_cannot_change_after_the_game_has_started(self):
        game = create_waiting_game(self.host, self.users[:2])
        add_player(game, self.users[2])
        self.initialize(game)
        player = game.players.first()

        for change in (lambda: add_player(game, self.users[3]), lambda: remove_player(player)):
            with self.assertRaises(ValidationError) as context:
                change()
            self.assertIn("invalid_status", error_codes(context.exception))
        self.assertEqual(game.players.count(), PLAYERS_COUNT)


class InitializationTriggerTests(InitializationTestCase):
    def test_management_command_initializes_the_game(self):
        out = StringIO()

        call_command("initialize_game", self.game.pk, "--seed", "3", stdout=out)

        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.IN_PROGRESS)
        self.assertIn("initialized", out.getvalue())
        for user in self.trio:
            self.assertIn(user.username, out.getvalue())

    def test_management_command_reports_rejections(self):
        with self.assertRaisesMessage(CommandError, "does not exist"):
            call_command("initialize_game", 999_999)

        game = create_waiting_game(self.host, self.users[:2])
        with self.assertRaisesMessage(CommandError, "exactly 3 players"):
            call_command("initialize_game", game.pk)
        self.assert_untouched(game)

    def test_admin_action_initializes_selected_games(self):
        admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="Str0ng-pass-123")
        not_ready = create_waiting_game(self.host, self.users[:2])
        self.client.force_login(admin)

        response = self.client.post(
            reverse("admin:games_game_changelist"),
            {"action": "initialize_games", "_selected_action": [self.game.pk, not_ready.pk]},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.IN_PROGRESS)
        self.assert_untouched(not_ready)
        messages = [str(message) for message in response.context["messages"]]
        self.assertTrue(any("initialized" in message for message in messages))
        self.assertTrue(any("exactly 3 players" in message for message in messages))

    def test_admin_inline_locks_players_after_start(self):
        admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="Str0ng-pass-123")
        request = RequestFactory().get("/")
        request.user = admin
        inline = GamePlayerInline(Game, site)

        self.assertTrue(inline.has_add_permission(request, self.game))
        self.assertTrue(inline.has_delete_permission(request, self.game))

        self.initialize()

        self.assertFalse(inline.has_add_permission(request, self.game))
        self.assertFalse(inline.has_change_permission(request, self.game))
        self.assertFalse(inline.has_delete_permission(request, self.game))


class SlowRandom(random.Random):
    """Holds the transaction open long enough for a concurrent attempt to collide with it."""

    def choice(self, seq):
        time.sleep(0.3)
        return super().choice(seq)


class ConcurrentInitializationTests(TransactionTestCase):
    """Real parallel attempts, each thread on its own database connection.

    On SQLite this relies on `transaction_mode: IMMEDIATE` (see settings): the second
    transaction waits for the first one's write lock instead of reading stale data.
    On PostgreSQL the `select_for_update` row lock gives the same result.
    """

    def setUp(self):
        self.host, *self.users = create_users("host", "ana", "boris", "vera")
        self.game = create_waiting_game(self.host, self.users)

    def run_in_parallel(self, *operations):
        barrier = threading.Barrier(len(operations))
        results = [None] * len(operations)

        def worker(index, operation):
            try:
                barrier.wait()
                operation()
                results[index] = "ok"
            except ValidationError as error:
                results[index] = error_codes(error)
            except Exception as error:  # noqa: BLE001 - reported to the test, not swallowed
                results[index] = error
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=item) for item in enumerate(operations)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    def test_two_simultaneous_initializations_create_one_map(self):
        game_id = self.game.pk

        results = self.run_in_parallel(
            lambda: initialize_game(Game.objects.get(pk=game_id), rng=SlowRandom(1)),
            lambda: initialize_game(Game.objects.get(pk=game_id), rng=SlowRandom(2)),
        )

        self.assertCountEqual(results, ["ok", ["invalid_status"]])
        self.assertEqual(Territory.objects.filter(game_id=game_id).count(), MAP_SIZE)
        self.assertEqual(Capital.objects.filter(player__game_id=game_id).count(), PLAYERS_COUNT)
        self.assertEqual(Territory.objects.filter(game_id=game_id).exclude(owner=None).count(), PLAYERS_COUNT)

    def test_player_leaving_during_initialization_never_breaks_three_players(self):
        game_id = self.game.pk
        leaving = self.game.players.last()

        results = self.run_in_parallel(
            lambda: initialize_game(Game.objects.get(pk=game_id), rng=SlowRandom(1)),
            lambda: remove_player(leaving),
        )

        self.game.refresh_from_db()
        if self.game.status == Game.IN_PROGRESS:
            self.assertEqual(results, ["ok", ["invalid_status"]])
            self.assertEqual(self.game.players.count(), PLAYERS_COUNT)
            self.assertEqual(Capital.objects.filter(player__game=self.game).count(), PLAYERS_COUNT)
        else:
            self.assertEqual(results, [["invalid_player_count"], "ok"])
            self.assertEqual(self.game.players.count(), PLAYERS_COUNT - 1)
            self.assertFalse(Territory.objects.filter(game=self.game).exists())
