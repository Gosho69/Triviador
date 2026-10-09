from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.test import TestCase

from games.models import Game, GamePlayer
from territories.map import ADJACENCIES, TERRITORIES
from territories.models import Adjacency, Capital, Territory

from .helpers import create_game_map

User = get_user_model()


class TerritoryTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.com", password="Str0ng-pass-123"
        )
        cls.guest = User.objects.create_user(
            username="guest", email="guest@example.com", password="Str0ng-pass-123"
        )
        cls.game = Game.objects.create(created_by=cls.host)
        cls.other_game = Game.objects.create(created_by=cls.guest)
        cls.player = GamePlayer.objects.create(game=cls.game, user=cls.host, player_order=1)
        cls.rival = GamePlayer.objects.create(game=cls.game, user=cls.guest, player_order=2)
        cls.outsider = GamePlayer.objects.create(game=cls.other_game, user=cls.guest, player_order=1)
        cls.territories = create_game_map(cls.game)
        cls.other_territories = create_game_map(cls.other_game)

    def assert_integrity_error(self, model, **fields):
        with self.assertRaises(IntegrityError), transaction.atomic():
            model.objects.create(**fields)


class TerritoryModelTests(TerritoryTestCase):
    def test_new_territory_has_no_owner_and_zero_score(self):
        territory = self.territories["sredets"]

        territory.full_clean()
        self.assertIsNone(territory.owner)
        self.assertEqual(territory.score, 0)
        self.assertEqual(str(territory), f"Средец (game #{self.game.pk})")

    def test_name_and_slug_are_unique_within_game(self):
        self.assert_integrity_error(Territory, game=self.game, name="Средец", slug="sredets-2")
        self.assert_integrity_error(Territory, game=self.game, name="Ново Средец", slug="sredets")
        with self.assertRaises(ValidationError):
            Territory(game=self.game, name="Средец", slug="sredets").full_clean()

    def test_same_name_and_slug_are_allowed_in_different_games(self):
        third_game = Game.objects.create(created_by=self.host)

        Territory(game=third_game, name="Средец", slug="sredets").full_clean()
        Territory.objects.create(game=third_game, name="Средец", slug="sredets")

    def test_owner_must_play_in_the_same_game(self):
        territory = self.territories["sredets"]
        territory.owner = self.outsider

        with self.assertRaises(ValidationError) as context:
            territory.full_clean()
        self.assertIn("owner", context.exception.message_dict)

        territory.owner = self.player
        territory.full_clean()

    def test_score_cannot_be_negative(self):
        with self.assertRaises(ValidationError) as context:
            Territory(game=self.game, name="Нова", slug="nova", score=-1).full_clean()
        self.assertIn("score", context.exception.message_dict)
        self.assert_integrity_error(Territory, game=self.game, name="Нова", slug="nova", score=-1)

    def test_neighbors_are_symmetric(self):
        skali = self.territories["skali"]
        dunaviya = self.territories["dunaviya"]

        self.assertIn(dunaviya, skali.neighbors.all())
        self.assertIn(skali, dunaviya.neighbors.all())
        self.assertEqual(Adjacency.objects.filter(from_territory__game=self.game).count(), 2 * len(ADJACENCIES))

    def test_territory_cannot_border_itself(self):
        skali = self.territories["skali"]

        # add() runs inside the caller's transaction, so a rejected add needs its own atomic block.
        with self.assertRaises(ValidationError), transaction.atomic():
            skali.neighbors.add(skali)
        with self.assertRaises(ValidationError):
            Adjacency.objects.create(from_territory=skali, to_territory=skali)
        # The database constraint holds even when the model layer is bypassed.
        with self.assertRaises(IntegrityError), transaction.atomic():
            QuerySet(model=Adjacency).bulk_create([Adjacency(from_territory=skali, to_territory=skali)])

    def test_territories_of_different_games_cannot_border(self):
        skali = self.territories["skali"]
        foreign = self.other_territories["kaliakra"]

        with self.assertRaises(ValidationError), transaction.atomic():
            skali.neighbors.add(foreign)
        with self.assertRaises(ValidationError):
            Adjacency(from_territory=skali, to_territory=foreign).full_clean()
        with self.assertRaises(ValidationError):
            Adjacency.objects.create(from_territory=skali, to_territory=foreign)
        with self.assertRaises(ValidationError):
            Adjacency.objects.bulk_create([Adjacency(from_territory=skali, to_territory=foreign)])
        self.assertNotIn(foreign, skali.neighbors.all())

    def test_border_is_stored_once_per_direction(self):
        self.assert_integrity_error(
            Adjacency, from_territory=self.territories["skali"], to_territory=self.territories["dunaviya"]
        )

    def test_games_have_independent_state(self):
        territory = self.territories["sredets"]
        territory.owner = self.player
        territory.score = 200
        territory.save()

        other = self.other_territories["sredets"]
        other.refresh_from_db()
        self.assertIsNone(other.owner)
        self.assertEqual(other.score, 0)
        for first in self.territories.values():
            with self.subTest(first.slug):
                self.assertTrue(all(n.game_id == self.game.pk for n in first.neighbors.all()))

    def test_every_game_uses_the_same_project_map(self):
        for game in (self.game, self.other_game):
            with self.subTest(game=game.pk):
                self.assertEqual(set(game.territories.values_list("slug", "name")), set(TERRITORIES))
                borders = {
                    frozenset((territory.slug, neighbor.slug))
                    for territory in game.territories.prefetch_related("neighbors")
                    for neighbor in territory.neighbors.all()
                }
                self.assertEqual(borders, {frozenset(pair) for pair in ADJACENCIES})

    def test_deleting_game_deletes_its_territories_and_borders(self):
        self.other_game.delete()

        self.assertFalse(Territory.objects.filter(game_id=self.other_game.pk).exists())
        self.assertEqual(Territory.objects.count(), len(TERRITORIES))
        self.assertEqual(Adjacency.objects.count(), 2 * len(ADJACENCIES))

    def test_deleting_owner_leaves_territory_unowned(self):
        territory = self.territories["sredets"]
        territory.owner = self.rival
        territory.save()

        self.rival.delete()

        territory.refresh_from_db()
        self.assertIsNone(territory.owner)


class CapitalModelTests(TerritoryTestCase):
    def setUp(self):
        self.home = self.territories["skali"]
        self.home.owner = self.player
        self.home.save()

    def test_new_capital_has_full_health(self):
        capital = Capital.objects.create(territory=self.home, player=self.player)

        capital.full_clean()
        self.assertEqual(capital.health, Capital.MAX_HEALTH)
        self.assertEqual(capital.game, self.game)

    def test_health_must_be_between_zero_and_three(self):
        for health in (0, 3):
            with self.subTest(health=health):
                Capital(territory=self.home, player=self.player, health=health).full_clean()
        for health in (-1, 4):
            with self.subTest(health=health):
                with self.assertRaises(ValidationError) as context:
                    Capital(territory=self.home, player=self.player, health=health).full_clean()
                self.assertIn("health", context.exception.message_dict)
                self.assert_integrity_error(Capital, territory=self.home, player=self.player, health=health)

    def test_destroyed_capital_is_kept(self):
        capital = Capital.objects.create(territory=self.home, player=self.player, health=0)

        capital.full_clean()
        self.assertTrue(Capital.objects.filter(pk=capital.pk).exists())

    def test_destroyed_capital_may_stay_on_a_conquered_territory(self):
        capital = Capital.objects.create(territory=self.home, player=self.player, health=0)
        self.home.owner = self.rival
        self.home.save()

        capital.full_clean()
        self.home.full_clean()

    def test_territory_with_standing_capital_keeps_its_owner(self):
        Capital.objects.create(territory=self.home, player=self.player)

        for owner in (self.rival, None):
            with self.subTest(owner=owner):
                self.home.owner = owner
                with self.assertRaises(ValidationError) as context:
                    self.home.full_clean()
                self.assertIn("owner", context.exception.message_dict)

        self.home.owner = self.player
        self.home.full_clean()

    def test_capitals_cannot_border_each_other(self):
        Capital.objects.create(territory=self.home, player=self.player)
        neighbor, far_away = (self.territories[slug] for slug in ("dunaviya", "kaliakra"))
        for territory in (neighbor, far_away):
            territory.owner = self.rival
            territory.save()

        with self.assertRaises(ValidationError) as context:
            Capital(territory=neighbor, player=self.rival).full_clean()
        self.assertEqual(context.exception.message_dict["territory"], ["A capital cannot border another capital."])
        Capital(territory=far_away, player=self.rival).full_clean()

    def test_player_and_territory_have_at_most_one_capital(self):
        Capital.objects.create(territory=self.home, player=self.player)
        second = self.territories["kaliakra"]
        second.owner = self.player
        second.save()

        self.assert_integrity_error(Capital, territory=second, player=self.player)
        self.assert_integrity_error(Capital, territory=self.home, player=self.rival)

    def test_capital_must_be_consistent_with_its_territory(self):
        foreign = self.other_territories["tsarevo"]
        foreign.owner = self.outsider
        foreign.save()
        invalid_capitals = {
            "player from another game": ("player", {"territory": foreign, "player": self.player}),
            "territory owned by someone else": ("territory", {"territory": self.home, "player": self.rival}),
            "territory without owner": ("territory", {"territory": self.territories["tsarevo"], "player": self.rival}),
        }
        for case, (field, fields) in invalid_capitals.items():
            with self.subTest(case):
                with self.assertRaises(ValidationError) as context:
                    Capital(**fields).full_clean()
                self.assertIn(field, context.exception.message_dict)


class TerritoryAccessTests(TerritoryTestCase):
    def test_game_territories(self):
        self.assertEqual(self.game.territories.count(), len(TERRITORIES))
        self.assertNotIn(self.other_territories["skali"], self.game.territories.all())

    def test_player_owned_territories(self):
        Territory.objects.filter(pk__in=[self.territories["skali"].pk, self.territories["sredets"].pk]).update(
            owner=self.player
        )

        self.assertEqual(
            list(self.player.territories.values_list("slug", flat=True)), ["skali", "sredets"]
        )
        self.assertFalse(self.rival.territories.exists())

    def test_player_capital(self):
        home = self.territories["skali"]
        home.owner = self.player
        home.save()
        capital = Capital.objects.create(territory=home, player=self.player)

        self.assertEqual(Capital.for_player(self.player), capital)
        self.assertEqual(self.player.capital, capital)
        self.assertEqual(home.capital, capital)

    def test_missing_capital_returns_none(self):
        self.assertIsNone(Capital.for_player(self.rival))
        with self.assertRaises(Capital.DoesNotExist):
            self.rival.capital


class NoInitializationTests(TestCase):
    def test_creating_game_does_not_create_map_or_capitals(self):
        host = User.objects.create_user(username="solo", email="solo@example.com", password="Str0ng-pass-123")

        game = Game.objects.create(created_by=host)
        GamePlayer.objects.create(game=game, user=host, player_order=1)

        game.refresh_from_db()
        self.assertEqual(game.status, Game.WAITING)
        self.assertFalse(Territory.objects.exists())
        self.assertFalse(Capital.objects.exists())
