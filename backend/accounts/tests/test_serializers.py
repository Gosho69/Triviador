from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import serializers

from accounts.models import Profile
from accounts.serializers import ProfileUpdateSerializer, RegisterSerializer

User = get_user_model()


def registration_data(**overrides):
    data = {
        "username": "player_one",
        "email": "player@example.com",
        "nickname": "MountainKnight",
        "password": "Str0ng-pass-123",
        "password_confirm": "Str0ng-pass-123",
    }
    data.update(overrides)
    return data


class RegisterSerializerTests(TestCase):
    def test_creates_user_with_hashed_password_and_profile(self):
        serializer = RegisterSerializer(data=registration_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertNotEqual(user.password, "Str0ng-pass-123")
        self.assertTrue(user.check_password("Str0ng-pass-123"))
        self.assertEqual(user.profile.nickname, "MountainKnight")
        self.assertNotIn("password", serializer.data)
        self.assertNotIn("password_confirm", serializer.data)

    def test_rejects_weak_password(self):
        serializer = RegisterSerializer(
            data=registration_data(password="12345", password_confirm="12345")
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_email_and_nickname_checks_ignore_case(self):
        existing = User.objects.create_user(
            username="existing", email="taken@example.com", password="Str0ng-pass-123"
        )
        Profile.objects.create(user=existing, nickname="TakenName")

        serializer = RegisterSerializer(
            data=registration_data(email="TAKEN@example.com", nickname="takenname")
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("nickname", serializer.errors)


class ProfileUpdateSerializerTests(TestCase):
    def test_keeping_own_nickname_is_not_a_conflict(self):
        user = User.objects.create_user(
            username="player_one", email="player@example.com", password="Str0ng-pass-123"
        )
        profile = Profile.objects.create(user=user, nickname="MountainKnight")

        serializer = ProfileUpdateSerializer(
            profile, data={"nickname": "mountainknight"}, partial=True
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_unknown_avatar(self):
        user = User.objects.create_user(
            username="player_one", email="player@example.com", password="Str0ng-pass-123"
        )
        profile = Profile.objects.create(user=user, nickname="MountainKnight")

        serializer = ProfileUpdateSerializer(profile, data={"avatar_key": "dragon"}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn("avatar_key", serializer.errors)


class UniqueRaceTests(TestCase):
    """validate_* can pass for two racing requests; the DB constraint must still yield a 400-style error."""

    def test_create_maps_nickname_collision_to_field_error(self):
        existing = User.objects.create_user(
            username="existing", email="taken@example.com", password="Str0ng-pass-123"
        )
        Profile.objects.create(user=existing, nickname="TakenName")
        serializer = RegisterSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.create(
                {"username": "racer", "email": "racer@example.com", "nickname": "takenname", "password": "Str0ng-pass-123"}
            )

        self.assertIn("nickname", ctx.exception.detail)
        self.assertFalse(User.objects.filter(username="racer").exists())
