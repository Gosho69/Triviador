from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import Profile

User = get_user_model()

PASSWORD = "Str0ng-pass-123"

REGISTER_URL = reverse("accounts:register")
LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
ME_URL = reverse("accounts:me")
CSRF_URL = reverse("accounts:csrf")


def create_player(username="player_one", email="player@example.com", nickname="MountainKnight"):
    user = User.objects.create_user(username=username, email=email, password=PASSWORD)
    Profile.objects.create(user=user, nickname=nickname)
    return user


def registration_payload(**overrides):
    payload = {
        "username": "player_one",
        "email": "player@example.com",
        "nickname": "MountainKnight",
        "password": PASSWORD,
        "password_confirm": PASSWORD,
    }
    payload.update(overrides)
    return payload


class RegistrationTests(APITestCase):
    def test_successful_registration(self):
        response = self.client.post(REGISTER_URL, registration_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="player_one")
        self.assertEqual(user.profile.nickname, "MountainKnight")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(
            response.data,
            {
                "id": user.id,
                "username": "player_one",
                "email": "player@example.com",
                "profile": {"nickname": "MountainKnight", "avatar_key": "knight-1"},
            },
        )
        self.assertNotIn("password", response.content.decode())

    def test_invalid_registration(self):
        create_player(username="taken", email="taken@example.com", nickname="TakenKnight")
        cases = {
            "username": registration_payload(username="taken"),
            "email": registration_payload(email="taken@example.com"),
            "nickname": registration_payload(nickname="TakenKnight"),
            "password_confirm": registration_payload(password_confirm="different-pass-123"),
        }

        for error_field, payload in cases.items():
            with self.subTest(error_field=error_field):
                response = self.client.post(REGISTER_URL, payload, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(error_field, response.data["errors"])
                self.assertIsInstance(response.data["errors"][error_field], list)
                self.assertEqual(User.objects.count(), 1)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = create_player()

    def test_successful_login_creates_session(self):
        response = self.client.post(
            LOGIN_URL, {"username": "player_one", "password": PASSWORD}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("sessionid", response.cookies)
        self.assertEqual(response.data["id"], self.user.id)

        me = self.client.get(ME_URL)
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["username"], "player_one")
        self.assertEqual(me.data["profile"]["nickname"], "MountainKnight")

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            LOGIN_URL, {"username": "player_one", "password": "wrong-password"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])
        self.assertNotIn("sessionid", response.cookies)
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)


class MePermissionTests(APITestCase):
    def test_anonymous_user_is_denied(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data["errors"])

    def test_authenticated_user_sees_only_own_data(self):
        create_player(username="someone_else", email="else@example.com", nickname="OtherKnight")
        user = create_player()
        self.client.force_authenticate(user)

        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], user.id)
        self.assertEqual(response.data["profile"]["nickname"], "MountainKnight")


class ProfileUpdateTests(APITestCase):
    def test_updates_profile_but_not_protected_fields(self):
        user = create_player()
        self.client.force_authenticate(user)

        response = self.client.patch(
            ME_URL,
            {
                "nickname": "NewKnight",
                "avatar_key": "knight-3",
                "is_staff": True,
                "username": "hijacked",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"], {"nickname": "NewKnight", "avatar_key": "knight-3"})
        user.refresh_from_db()
        self.assertEqual(user.profile.nickname, "NewKnight")
        self.assertEqual(user.profile.avatar_key, "knight-3")
        self.assertFalse(user.is_staff)
        self.assertEqual(user.username, "player_one")


class LogoutTests(APITestCase):
    def test_logout_ends_session(self):
        create_player()
        self.client.login(username="player_one", password=PASSWORD)

        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)


class CsrfTests(APITestCase):
    def setUp(self):
        create_player()
        self.client = APIClient(enforce_csrf_checks=True)

    def test_unsafe_request_requires_csrf_token(self):
        self.client.login(username="player_one", password=PASSWORD)

        without_token = self.client.patch(ME_URL, {"nickname": "NoToken"}, format="json")

        self.assertEqual(without_token.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", without_token.data["errors"])

        csrf_response = self.client.get(CSRF_URL)
        self.assertEqual(csrf_response.status_code, status.HTTP_204_NO_CONTENT)
        token = self.client.cookies["csrftoken"].value

        with_token = self.client.patch(
            ME_URL, {"nickname": "WithToken"}, format="json", HTTP_X_CSRFTOKEN=token
        )

        self.assertEqual(with_token.status_code, status.HTTP_200_OK)
        self.assertEqual(with_token.data["profile"]["nickname"], "WithToken")

    def test_login_requires_csrf_token(self):
        credentials = {"username": "player_one", "password": PASSWORD}

        without_token = self.client.post(LOGIN_URL, credentials, format="json")
        self.assertEqual(without_token.status_code, status.HTTP_403_FORBIDDEN)

        self.client.get(CSRF_URL)
        token = self.client.cookies["csrftoken"].value
        with_token = self.client.post(LOGIN_URL, credentials, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(with_token.status_code, status.HTTP_200_OK)
