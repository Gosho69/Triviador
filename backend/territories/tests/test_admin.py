from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from games.models import Game, GamePlayer
from territories.models import Capital, Territory

from .helpers import create_game_map

User = get_user_model()


class TerritoryAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="Str0ng-pass-123"
        )
        cls.guest = User.objects.create_user(
            username="guest", email="guest@example.com", password="Str0ng-pass-123"
        )
        cls.game = Game.objects.create(created_by=cls.admin)
        cls.other_game = Game.objects.create(created_by=cls.guest)
        cls.player = GamePlayer.objects.create(game=cls.game, user=cls.guest, player_order=1)
        cls.territories = create_game_map(cls.game)
        create_game_map(cls.other_game)

        cls.home = cls.territories["skali"]
        cls.home.owner = cls.player
        cls.home.save()
        cls.capital = Capital.objects.create(territory=cls.home, player=cls.player)

    def setUp(self):
        self.client.force_login(self.admin)

    def changelist(self, model, **params):
        url = reverse(f"admin:territories_{model}_changelist")
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200)
        return list(response.context["cl"].result_list)

    def test_territory_search_by_name_and_slug(self):
        for query in ("Средец", "sredets"):
            with self.subTest(query):
                results = self.changelist("territory", q=query)
                self.assertEqual({t.slug for t in results}, {"sredets"})
                self.assertEqual(len(results), 2)

    def test_territory_filter_by_game_and_owner(self):
        by_game = self.changelist("territory", game__id__exact=self.game.pk)
        by_owner = self.changelist("territory", owner__id__exact=self.player.pk)

        self.assertEqual(len(by_game), len(self.territories))
        self.assertTrue(all(t.game_id == self.game.pk for t in by_game))
        self.assertEqual(by_owner, [self.home])

    def test_owner_filter_query_count_does_not_grow_with_owners(self):
        url = reverse("admin:territories_territory_changelist")

        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                self.client.get(url)
            return len(queries)

        baseline = count_queries()
        for order, slug in enumerate(("kaliakra", "tsarevo", "pirina"), start=2):
            user = User.objects.create_user(username=f"p{order}", email=f"p{order}@example.com")
            player = GamePlayer.objects.create(game=self.game, user=user, player_order=order)
            Territory.objects.filter(pk=self.territories[slug].pk).update(owner=player)

        self.assertEqual(count_queries(), baseline)

    def test_territory_list_shows_neighbors(self):
        url = reverse("admin:territories_territory_changelist")

        response = self.client.get(url, {"q": "skali", "game__id__exact": self.game.pk})

        self.assertContains(response, "Дунавия, Средец")

    def test_capital_search_and_filter(self):
        for query in ("guest", "Скали", "skali"):
            with self.subTest(query):
                self.assertEqual(self.changelist("capital", q=query), [self.capital])
        self.assertEqual(self.changelist("capital", territory__game__id__exact=self.game.pk), [self.capital])
        self.assertEqual(self.changelist("capital", territory__game__id__exact=self.other_game.pk), [])

    def test_map_structure_cannot_be_added_or_deleted(self):
        urls = [
            reverse("admin:territories_territory_add"),
            reverse("admin:territories_territory_delete", args=[self.home.pk]),
            reverse("admin:territories_capital_add"),
            reverse("admin:territories_capital_delete", args=[self.capital.pk]),
        ]
        for url in urls:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_delete_ui_is_hidden(self):
        change = reverse("admin:territories_territory_change", args=[self.home.pk])
        changelist = reverse("admin:territories_territory_changelist")

        self.assertNotContains(self.client.get(change), "deletelink")
        self.assertNotContains(self.client.get(changelist), 'value="delete_selected"')

    def test_deleting_game_in_admin_cascades_to_its_map(self):
        url = reverse("admin:games_game_delete", args=[self.game.pk])

        self.assertEqual(self.client.get(url).context["perms_lacking"], set())
        response = self.client.post(url, {"post": "yes"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Territory.objects.filter(game_id=self.game.pk).exists())
        self.assertFalse(Capital.objects.exists())
        self.assertTrue(Territory.objects.filter(game=self.other_game).exists())

    def test_only_score_is_editable_on_territory(self):
        url = reverse("admin:territories_territory_change", args=[self.home.pk])

        response = self.client.get(url)

        self.assertEqual(list(response.context["adminform"].form.fields), ["score"])
        response = self.client.post(url, {"score": 300, "name": "Хакнато", "owner": ""})
        self.assertEqual(response.status_code, 302)
        self.home.refresh_from_db()
        self.assertEqual((self.home.score, self.home.name, self.home.owner), (300, "Скали", self.player))
        self.assertEqual(self.home.neighbors.count(), 2)

    def test_negative_score_is_rejected(self):
        url = reverse("admin:territories_territory_change", args=[self.home.pk])

        response = self.client.post(url, {"score": -5})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["adminform"].form.errors)
        self.home.refresh_from_db()
        self.assertEqual(self.home.score, 0)

    def test_only_health_is_editable_on_capital(self):
        url = reverse("admin:territories_capital_change", args=[self.capital.pk])

        self.assertEqual(list(self.client.get(url).context["adminform"].form.fields), ["health"])
        for health, status in ((4, 200), (-1, 200), (0, 302)):
            with self.subTest(health=health):
                response = self.client.post(url, {"health": health})
                self.assertEqual(response.status_code, status)
        self.capital.refresh_from_db()
        self.assertEqual(self.capital.health, 0)
