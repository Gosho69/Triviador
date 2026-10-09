from rest_framework import serializers

from territories.map import TERRITORIES

from .models import Game, GamePlayer
from .services import PLAYERS_COUNT

# Territories are sent in project-map order, so clients can lay the board out by position.
MAP_ORDER = {slug: index for index, (slug, _) in enumerate(TERRITORIES)}


class PlayerSerializer(serializers.ModelSerializer):
    seat = serializers.IntegerField(source="player_order")
    nickname = serializers.SerializerMethodField()
    avatar_key = serializers.SerializerMethodField()
    is_you = serializers.SerializerMethodField()
    is_host = serializers.SerializerMethodField()

    class Meta:
        model = GamePlayer
        fields = ("seat", "nickname", "avatar_key", "is_you", "is_host")
        read_only_fields = fields

    # Accounts made with `createsuperuser` have no profile; fall back to the username.
    def get_nickname(self, player):
        profile = getattr(player.user, "profile", None)
        return profile.nickname if profile else player.user.username

    def get_avatar_key(self, player):
        profile = getattr(player.user, "profile", None)
        return profile.avatar_key if profile else None

    def get_is_you(self, player):
        return player.user_id == self.context["request"].user.id

    def get_is_host(self, player):
        return player.user_id == player.game.created_by_id


class GameSerializer(serializers.ModelSerializer):
    is_host = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    # Clients draw this many seats, so the player limit is defined only on the server.
    seats = serializers.SerializerMethodField()
    players = PlayerSerializer(many=True)

    class Meta:
        model = Game
        fields = ("id", "status", "is_host", "is_member", "seats", "players")
        read_only_fields = fields

    def get_is_host(self, game):
        return game.created_by_id == self.context["request"].user.id

    def get_seats(self, game):
        return PLAYERS_COUNT

    def get_is_member(self, game):
        user_id = self.context["request"].user.id
        return any(player.user_id == user_id for player in game.players.all())


class GameDetailSerializer(GameSerializer):
    board = serializers.SerializerMethodField()

    class Meta(GameSerializer.Meta):
        fields = (*GameSerializer.Meta.fields, "board")
        read_only_fields = fields

    def get_board(self, game):
        if game.status == Game.WAITING:
            return None
        territories = sorted(
            game.territories.all(), key=lambda territory: MAP_ORDER.get(territory.slug, len(MAP_ORDER))
        )
        if not territories:
            return None
        return {"territories": [self._territory(territory) for territory in territories]}

    @staticmethod
    def _territory(territory):
        capital = getattr(territory, "capital", None)
        return {
            "slug": territory.slug,
            "name": territory.name,
            "owner_seat": territory.owner.player_order if territory.owner else None,
            "neighbors": sorted(neighbor.slug for neighbor in territory.neighbors.all()),
            "capital": {"health": capital.health, "max_health": capital.MAX_HEALTH} if capital else None,
        }
