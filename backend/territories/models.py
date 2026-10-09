from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import F, Q

from games.models import Game, GamePlayer

CAPITAL_MAX_HEALTH = 3


class Territory(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="territories")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    owner = models.ForeignKey(
        GamePlayer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="territories",
    )
    score = models.PositiveIntegerField(default=0)
    neighbors = models.ManyToManyField(
        "self",
        through="Adjacency",
        through_fields=("from_territory", "to_territory"),
        symmetrical=True,
        blank=True,
    )

    class Meta:
        ordering = ["game_id", "slug"]
        verbose_name_plural = "territories"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "name"],
                name="territories_territory_game_name_unique",
                violation_error_message="A territory with this name already exists in the game.",
            ),
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="territories_territory_game_slug_unique",
                violation_error_message="A territory with this slug already exists in the game.",
            ),
        ]

    def __str__(self):
        return f"{self.name} (game #{self.game_id})"

    def clean(self):
        super().clean()
        if self.owner_id and self.game_id and self.owner.game_id != self.game_id:
            raise ValidationError({"owner": "The owner must be a player in the territory's game."})
        if self.pk and self.has_live_capital_of_another_player():
            raise ValidationError({"owner": "A territory with a standing capital must stay with the capital's player."})

    def has_live_capital_of_another_player(self):
        return (
            Capital.objects.filter(territory_id=self.pk, health__gt=0)
            .exclude(player_id=self.owner_id)
            .exists()
        )


def validate_borders(adjacencies):
    """Reject self and cross-game borders. Runs on every insert path, not only in full_clean()."""
    if any(adjacency.from_territory_id == adjacency.to_territory_id for adjacency in adjacencies):
        raise ValidationError("A territory cannot border itself.", code="self_adjacency")

    territory_ids = {
        territory_id
        for adjacency in adjacencies
        for territory_id in (adjacency.from_territory_id, adjacency.to_territory_id)
    }
    game_by_territory = dict(Territory.objects.filter(pk__in=territory_ids).values_list("pk", "game_id"))
    if any(
        game_by_territory.get(adjacency.from_territory_id) != game_by_territory.get(adjacency.to_territory_id)
        for adjacency in adjacencies
    ):
        raise ValidationError("Neighbouring territories must belong to the same game.", code="cross_game_adjacency")


class AdjacencyQuerySet(models.QuerySet):
    def bulk_create(self, objs, *args, **kwargs):
        # `neighbors.add()` inserts through this method as well.
        objs = list(objs)
        validate_borders(objs)
        return super().bulk_create(objs, *args, **kwargs)


class Adjacency(models.Model):
    """One direction of a border; the symmetric `neighbors` relation stores both."""

    from_territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name="+")
    to_territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name="+")

    objects = AdjacencyQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "adjacencies"
        constraints = [
            models.UniqueConstraint(
                fields=["from_territory", "to_territory"],
                name="territories_adjacency_pair_unique",
                violation_error_message="These territories are already neighbours.",
            ),
            models.CheckConstraint(
                condition=~Q(from_territory=F("to_territory")),
                name="territories_adjacency_not_self",
                violation_error_message="A territory cannot border itself.",
            ),
        ]

    def __str__(self):
        return f"{self.from_territory} → {self.to_territory}"

    def clean(self):
        super().clean()
        if self.from_territory_id and self.to_territory_id:
            validate_borders([self])

    def save(self, *args, **kwargs):
        validate_borders([self])
        super().save(*args, **kwargs)


class Capital(models.Model):
    MAX_HEALTH = CAPITAL_MAX_HEALTH

    territory = models.OneToOneField(Territory, on_delete=models.CASCADE, related_name="capital")
    player = models.OneToOneField(GamePlayer, on_delete=models.CASCADE, related_name="capital")
    health = models.PositiveSmallIntegerField(
        default=MAX_HEALTH,
        validators=[MaxValueValidator(MAX_HEALTH)],
    )

    class Meta:
        ordering = ["territory__game_id", "player__player_order"]
        constraints = [
            # PositiveSmallIntegerField already rejects negative health in the database.
            models.CheckConstraint(
                condition=Q(health__lte=CAPITAL_MAX_HEALTH),
                name="territories_capital_health_max",
                violation_error_message=f"Capital health cannot exceed {CAPITAL_MAX_HEALTH}.",
            ),
        ]

    def __str__(self):
        return f"Capital of {self.player} at {self.territory.name}"

    @property
    def game(self):
        return self.territory.game

    @classmethod
    def for_player(cls, player):
        """Return the player's capital, or None while it has not been assigned."""
        return cls.objects.select_related("territory").filter(player=player).order_by().first()

    def borders_another_capital(self):
        # Capitals never move, so the non-adjacent starting positions hold for the whole game.
        return (
            Capital.objects.filter(territory__in=self.territory.neighbors.all())
            .exclude(pk=self.pk)
            .exists()
        )

    def clean(self):
        super().clean()
        if not (self.territory_id and self.player_id):
            return

        errors = {}
        if self.player.game_id != self.territory.game_id:
            errors["player"] = "The player must belong to the territory's game."
        elif self.health > 0 and self.territory.owner_id != self.player_id:
            # A destroyed capital stays on record after its territory changes hands.
            errors["territory"] = "A standing capital must be on a territory owned by its player."
        elif self.borders_another_capital():
            errors["territory"] = "A capital cannot border another capital."

        if errors:
            raise ValidationError(errors)
