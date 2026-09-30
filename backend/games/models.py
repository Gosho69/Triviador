from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from questions.models import AnswerOption, ChoiceQuestion, NumericQuestion


class Game(models.Model):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (WAITING, "Waiting"),
        (IN_PROGRESS, "In Progress"),
        (FINISHED, "Finished"),
        (CANCELLED, "Cancelled"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_games",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=WAITING)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Game #{self.pk} ({self.get_status_display()})"


class GamePlayer(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="players")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="game_players",
    )
    player_order = models.PositiveSmallIntegerField()
    score = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["game_id", "player_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "user"],
                name="games_gameplayer_game_user_unique",
                violation_error_message="This user has already joined the game.",
            ),
            models.UniqueConstraint(
                fields=["game", "player_order"],
                name="games_gameplayer_game_order_unique",
                violation_error_message="This player order is already taken in the game.",
            ),
        ]

    def __str__(self):
        return f"{self.user} in game #{self.game_id}"


class Round(models.Model):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    EVALUATED = "evaluated"

    ROUND_STATUS_CHOICES = [
        (PENDING, "Pending"),
        (OPEN, "Open"),
        (CLOSED, "Closed"),
        (EVALUATED, "Evaluated"),
    ]

    CHOICE = "choice"
    NUMERIC = "numeric"

    QUESTION_TYPE_CHOICES = [
        (CHOICE, "Choice"),
        (NUMERIC, "Numeric"),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="rounds")
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ROUND_STATUS_CHOICES, default=PENDING)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    choice_question = models.ForeignKey(
        ChoiceQuestion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rounds",
    )
    numeric_question = models.ForeignKey(
        NumericQuestion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rounds",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["game_id", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "number"],
                name="games_round_game_number_unique",
                violation_error_message="A round with this number already exists in the game.",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        question_type="choice",
                        choice_question__isnull=False,
                        numeric_question__isnull=True,
                    )
                    | Q(
                        question_type="numeric",
                        numeric_question__isnull=False,
                        choice_question__isnull=True,
                    )
                ),
                name="games_round_question_matches_type",
                violation_error_message="A round must have exactly one question matching its question type.",
            ),
        ]

    def __str__(self):
        return f"Round {self.number} of game #{self.game_id}"

    @property
    def question(self):
        if self.question_type == self.CHOICE:
            return self.choice_question
        return self.numeric_question


class RoundAnswer(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="answers")
    player = models.ForeignKey(GamePlayer, on_delete=models.CASCADE, related_name="answers")
    selected_option = models.ForeignKey(
        AnswerOption,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="round_answers",
    )
    numeric_value = models.IntegerField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["round_id", "player__player_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["round", "player"],
                name="games_roundanswer_round_player_unique",
                violation_error_message="This player has already answered the round.",
            ),
            models.CheckConstraint(
                condition=Q(selected_option__isnull=True) | Q(numeric_value__isnull=True),
                name="games_roundanswer_single_answer_kind",
                violation_error_message="An answer can have either a selected option or a numeric value, not both.",
            ),
        ]

    def __str__(self):
        return f"{self.player} — round {self.round.number}"

    def clean(self):
        super().clean()
        if not (self.round_id and self.player_id):
            return

        errors = {}
        if self.player.game_id != self.round.game_id:
            errors["player"] = "The player must belong to the round's game."

        if self.round.question_type == Round.CHOICE:
            if self.numeric_value is not None:
                errors["numeric_value"] = "A choice round cannot have a numeric answer."
            if self.selected_option_id and self.selected_option.question_id != self.round.choice_question_id:
                errors["selected_option"] = "The selected option must belong to the round's question."
        elif self.selected_option_id:
            errors["selected_option"] = "A numeric round cannot have a selected option."

        if errors:
            raise ValidationError(errors)
