import random

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from games.models import Game
from games.services import initialize_game
from territories.models import Capital


class Command(BaseCommand):
    help = "Build a waiting game's map, assign its three capitals and start it."

    def add_arguments(self, parser):
        parser.add_argument("game_id", type=int)
        parser.add_argument("--seed", type=int, help="Seed the capital choice for a reproducible result.")

    def handle(self, *args, game_id, seed, **options):
        try:
            game = Game.objects.get(pk=game_id)
        except Game.DoesNotExist as error:
            raise CommandError(f"Game #{game_id} does not exist.") from error

        rng = random.Random(seed) if seed is not None else None
        try:
            initialize_game(game, rng=rng)
        except ValidationError as error:
            raise CommandError(f"Game #{game_id} was not initialized: {' '.join(error.messages)}") from error

        self.stdout.write(self.style.SUCCESS(f"{game} initialized with {game.territories.count()} territories."))
        capitals = Capital.objects.filter(player__game=game).select_related("player__user", "territory")
        for capital in capitals:
            self.stdout.write(f"  {capital.player.user}: {capital.territory.name}")
