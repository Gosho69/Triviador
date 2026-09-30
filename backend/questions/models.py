from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import Truncator

ANSWER_OPTIONS_COUNT = 4


def validate_answer_options(options):
    """Require exactly ANSWER_OPTIONS_COUNT options with exactly one marked correct."""
    options = list(options)
    errors = []

    if len(options) != ANSWER_OPTIONS_COUNT:
        errors.append(
            ValidationError(
                "A choice question must have exactly %(expected)d answer options.",
                code="invalid_option_count",
                params={"expected": ANSWER_OPTIONS_COUNT},
            )
        )

    if sum(option.is_correct for option in options) != 1:
        errors.append(
            ValidationError(
                "A choice question must have exactly one correct answer option.",
                code="invalid_correct_count",
            )
        )

    if errors:
        raise ValidationError(errors)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class BaseQuestion(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="%(class)ss",
    )
    text = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return Truncator(self.text).chars(60)


class ChoiceQuestion(BaseQuestion):
    def clean(self):
        super().clean()
        # Options reference the question, so they can only exist once it is saved.
        if self.pk:
            validate_answer_options(self.answer_options.all())


class NumericQuestion(BaseQuestion):
    correct_answer = models.IntegerField()


class AnswerOption(models.Model):
    question = models.ForeignKey(
        ChoiceQuestion,
        on_delete=models.CASCADE,
        related_name="answer_options",
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text
