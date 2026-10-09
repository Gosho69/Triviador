from contextlib import contextmanager

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch, Q, prefetch_related_objects
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from territories.models import Territory

from .models import Game, GamePlayer
from .serializers import GameDetailSerializer, GameSerializer
from .services import add_player, cancel_game, create_game, initialize_game, remove_player

PLAYERS = Prefetch("players", queryset=GamePlayer.objects.select_related("user__profile"))
TERRITORIES = Prefetch(
    "territories",
    queryset=Territory.objects.select_related("owner", "capital").prefetch_related(
        Prefetch("neighbors", queryset=Territory.objects.only("id", "slug"))
    ),
)


def visible_games(user):
    """Waiting games are open to everyone; any other game only to its players."""
    return Game.objects.filter(Q(status=Game.WAITING) | Q(players__user=user)).distinct()


@contextmanager
def service_errors():
    """Report a rejected game operation in the API's usual error shape."""
    try:
        yield
    except DjangoValidationError as error:
        raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: error.messages}) from error


def detail_response(request, pk, status_code=status.HTTP_200_OK):
    game = get_object_or_404(visible_games(request.user).prefetch_related(PLAYERS), pk=pk)
    # A waiting game has no board yet; skip the territory queries on every waiting-room poll.
    if game.status != Game.WAITING:
        prefetch_related_objects([game], TERRITORIES)
    return Response(GameDetailSerializer(game, context={"request": request}).data, status=status_code)


def ensure_host(request, game, action):
    if game.created_by_id != request.user.id:
        raise PermissionDenied(f"Only the host can {action} the game.")


class GameListView(APIView):
    def get(self, request):
        games = (
            Game.objects.filter(
                Q(status=Game.WAITING) | Q(status=Game.IN_PROGRESS, players__user=request.user)
            )
            .distinct()
            .prefetch_related(PLAYERS)
        )
        return Response(GameSerializer(games, many=True, context={"request": request}).data)

    def post(self, request):
        game = create_game(request.user)
        return detail_response(request, game.pk, status.HTTP_201_CREATED)


class GameDetailView(APIView):
    def get(self, request, pk):
        return detail_response(request, pk)


class JoinGameView(APIView):
    def post(self, request, pk):
        game = get_object_or_404(visible_games(request.user), pk=pk)
        with service_errors():
            add_player(game, request.user)
        return detail_response(request, pk)


class LeaveGameView(APIView):
    def post(self, request, pk):
        game = get_object_or_404(visible_games(request.user), pk=pk)
        player = game.players.filter(user=request.user).first()
        if player is None:
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: ["You are not in this game."]})
        with service_errors():
            remove_player(player)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StartGameView(APIView):
    def post(self, request, pk):
        game = get_object_or_404(visible_games(request.user), pk=pk)
        ensure_host(request, game, "start")
        with service_errors():
            initialize_game(game)
        return detail_response(request, pk)


class CancelGameView(APIView):
    def post(self, request, pk):
        game = get_object_or_404(visible_games(request.user), pk=pk)
        ensure_host(request, game, "cancel")
        with service_errors():
            cancel_game(game)
        return Response(status=status.HTTP_204_NO_CONTENT)
