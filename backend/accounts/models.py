from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    email = models.EmailField(unique=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
                violation_error_message="A user with this email already exists.",
            ),
        ]


class Profile(models.Model):
    class Avatar(models.TextChoices):
        KNIGHT_1 = "knight-1", "Knight 1"
        KNIGHT_2 = "knight-2", "Knight 2"
        KNIGHT_3 = "knight-3", "Knight 3"
        KNIGHT_4 = "knight-4", "Knight 4"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    nickname = models.CharField(max_length=30, unique=True)
    avatar_key = models.CharField(
        max_length=30,
        choices=Avatar.choices,
        default=Avatar.KNIGHT_1,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("nickname"),
                name="accounts_profile_nickname_ci_unique",
                violation_error_message="A profile with this nickname already exists.",
            ),
        ]

    def __str__(self):
        return self.nickname
