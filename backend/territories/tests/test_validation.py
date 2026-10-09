from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.test import TestCase

from games.models import Game
from territories.models import Adjacency, Capital, Territory
from territories.validation import validate_game_map

from .helpers import create_game_map

User = get_user_model()


class GameMapValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.com", password="Str0ng-pass-123"
        )

    def setUp(self):
        self.game = Game.objects.create(created_by=self.host)
        self.territories = create_game_map(self.game)

    def assert_invalid(self, code):
        with self.assertRaises(ValidationError) as context:
            validate_game_map(self.game)
        self.assertIn(code, [error.code for error in context.exception.error_list])

    def test_map_built_from_definition_is_valid(self):
        validate_game_map(self.game)

    def test_empty_game_is_invalid(self):
        empty_game = Game.objects.create(created_by=self.host)

        with self.assertRaises(ValidationError):
            validate_game_map(empty_game)

    def test_missing_territory_is_rejected(self):
        self.territories["tsarevo"].delete()

        self.assert_invalid("territory_mismatch")

    def test_renamed_territory_is_rejected(self):
        Territory.objects.filter(pk=self.territories["sredets"].pk).update(name="София")

        self.assert_invalid("territory_mismatch")

    def test_extra_territory_is_rejected(self):
        Territory.objects.create(game=self.game, name="Остров", slug="ostrov")

        self.assert_invalid("territory_mismatch")

    def test_wrong_borders_are_rejected_even_with_correct_count(self):
        skali, dunaviya, tsarevo = (self.territories[s] for s in ("skali", "dunaviya", "tsarevo"))
        skali.neighbors.remove(dunaviya)
        skali.neighbors.add(tsarevo)

        self.assert_invalid("adjacency_mismatch")

    def test_one_directional_border_is_rejected(self):
        Adjacency.objects.filter(
            from_territory=self.territories["skali"], to_territory=self.territories["dunaviya"]
        ).delete()

        self.assert_invalid("asymmetric_adjacency")

    def test_cross_game_border_is_rejected(self):
        other_game = Game.objects.create(created_by=self.host)
        foreign = Territory.objects.create(game=other_game, name="Чужда", slug="chuzhda")
        # The model layer refuses such rows, so write them past it to simulate corrupted data.
        QuerySet(model=Adjacency).bulk_create(
            [
                Adjacency(from_territory=self.territories["skali"], to_territory=foreign),
                Adjacency(from_territory=self.territories["kaliakra"], to_territory=foreign),
            ]
        )

        with self.assertRaises(ValidationError) as context:
            validate_game_map(self.game)
        # The valid borders are still compared, so the cross-game rows are the only problem reported.
        self.assertEqual([error.code for error in context.exception.error_list], ["cross_game_adjacency"])

    def test_validation_does_not_change_anything(self):
        game_state = (self.game.status, self.game.started_at)
        Territory.objects.filter(pk=self.territories["tsarevo"].pk).update(name="Друго")

        with self.assertRaises(ValidationError):
            validate_game_map(self.game)

        self.game.refresh_from_db()
        self.assertEqual((self.game.status, self.game.started_at), game_state)
        self.assertEqual(self.game.territories.count(), len(self.territories))
        self.assertFalse(self.game.territories.exclude(owner=None).exists())
        self.assertFalse(Capital.objects.exists())
