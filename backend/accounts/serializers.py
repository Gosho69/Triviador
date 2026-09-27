from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Profile

User = get_user_model()


UNIQUE_FIELD_MESSAGES = {
    "nickname": "Profile with this nickname already exists.",
    "email": "User with this email already exists.",
    "username": "A user with that username already exists.",
}


def _unique_violation(error):
    """Turn a unique-constraint IntegrityError (two requests racing) into a field error."""
    message = str(error).lower()
    for field, text in UNIQUE_FIELD_MESSAGES.items():
        if field in message:
            return serializers.ValidationError({field: [text]})
    raise error


def _validate_unique_nickname(value, exclude_pk=None):
    nicknames = Profile.objects.filter(nickname__iexact=value)
    if exclude_pk is not None:
        nicknames = nicknames.exclude(pk=exclude_pk)
    if nicknames.exists():
        raise serializers.ValidationError(UNIQUE_FIELD_MESSAGES["nickname"])
    return value


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("nickname", "avatar_key")


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "profile")
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    # Declared explicitly so the case-insensitive check in validate_email() is the only one.
    email = serializers.EmailField(max_length=254)
    nickname = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("username", "email", "nickname", "password", "password_confirm")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(UNIQUE_FIELD_MESSAGES["email"])
        return value

    def validate_nickname(self, value):
        return _validate_unique_nickname(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": ["Passwords do not match."]})

        candidate = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=validated_data["username"],
                    email=validated_data["email"],
                    password=validated_data["password"],
                )
                Profile.objects.create(user=user, nickname=validated_data["nickname"])
        except IntegrityError as error:
            raise _unique_violation(error)
        return user

    def to_representation(self, instance):
        return UserSerializer(instance).data


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Only the profile's own fields are writable; everything else in the body is ignored."""

    # Declared explicitly so the case-insensitive check in validate_nickname() is the only one.
    nickname = serializers.CharField(max_length=30)

    class Meta:
        model = Profile
        fields = ("nickname", "avatar_key")

    def validate_nickname(self, value):
        return _validate_unique_nickname(value, exclude_pk=self.instance.pk if self.instance else None)

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError as error:
            raise _unique_violation(error)
