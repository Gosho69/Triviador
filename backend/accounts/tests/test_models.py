from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Profile

User = get_user_model()


class CaseInsensitiveUniquenessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="player_one", email="player@example.com", password="Str0ng-pass-123"
        )
        Profile.objects.create(user=self.user, nickname="MountainKnight")

    def test_email_is_unique_regardless_of_case(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username="player_two", email="PLAYER@example.com", password="Str0ng-pass-123"
            )

    def test_nickname_is_unique_regardless_of_case(self):
        other = User.objects.create_user(
            username="player_two", email="two@example.com", password="Str0ng-pass-123"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Profile.objects.create(user=other, nickname="mountainknight")

    def test_new_profile_gets_default_avatar(self):
        self.assertEqual(self.user.profile.avatar_key, Profile.Avatar.KNIGHT_1)
