from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from games.models import Game, GamePlayer, Round, RoundAnswer
from questions.models import AnswerOption, Category, ChoiceQuestion, NumericQuestion

User = get_user_model()


class GameConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.com", password="Str0ng-pass-123"
        )
        cls.guest = User.objects.create_user(
            username="guest", email="guest@example.com", password="Str0ng-pass-123"
        )
        category = Category.objects.create(name="Наука")
        cls.choice_question = ChoiceQuestion.objects.create(
            category=category, text="Кой е химичният символ на златото?"
        )
        cls.option = AnswerOption.objects.create(
            question=cls.choice_question, text="Au", is_correct=True
        )
        other_question = ChoiceQuestion.objects.create(
            category=category, text="Коя е най-голямата планета?"
        )
        cls.foreign_option = AnswerOption.objects.create(
            question=other_question, text="Юпитер", is_correct=True
        )
        cls.numeric_question = NumericQuestion.objects.create(
            category=category, text="Колко планети има в Слънчевата система?", correct_answer=8
        )

        cls.game = Game.objects.create(created_by=cls.host)
        cls.player = GamePlayer.objects.create(game=cls.game, user=cls.host, player_order=1)
        cls.choice_round = Round.objects.create(
            game=cls.game,
            number=1,
            question_type=Round.CHOICE,
            choice_question=cls.choice_question,
        )
        cls.numeric_round = Round.objects.create(
            game=cls.game,
            number=2,
            question_type=Round.NUMERIC,
            numeric_question=cls.numeric_question,
        )

    def assert_integrity_error(self, model, **fields):
        with self.assertRaises(IntegrityError), transaction.atomic():
            model.objects.create(**fields)

    def test_user_can_join_game_only_once(self):
        self.assert_integrity_error(GamePlayer, game=self.game, user=self.host, player_order=2)

    def test_player_order_is_unique_within_game(self):
        self.assert_integrity_error(GamePlayer, game=self.game, user=self.guest, player_order=1)

    def test_player_order_can_repeat_across_games(self):
        other_game = Game.objects.create(created_by=self.guest)

        GamePlayer.objects.create(game=other_game, user=self.guest, player_order=1)

    def test_round_number_is_unique_within_game(self):
        self.assert_integrity_error(
            Round,
            game=self.game,
            number=1,
            question_type=Round.NUMERIC,
            numeric_question=self.numeric_question,
        )

    def test_round_must_have_exactly_one_question_matching_its_type(self):
        invalid_rounds = {
            "no question": {"question_type": Round.CHOICE},
            "both questions": {
                "question_type": Round.CHOICE,
                "choice_question": self.choice_question,
                "numeric_question": self.numeric_question,
            },
            "numeric question on choice round": {
                "question_type": Round.CHOICE,
                "numeric_question": self.numeric_question,
            },
            "choice question on numeric round": {
                "question_type": Round.NUMERIC,
                "choice_question": self.choice_question,
            },
        }
        for case, fields in invalid_rounds.items():
            with self.subTest(case):
                with self.assertRaises(ValidationError):
                    Round(game=self.game, number=3, **fields).full_clean()
                self.assert_integrity_error(Round, game=self.game, number=3, **fields)

    def test_player_can_answer_round_only_once(self):
        RoundAnswer.objects.create(round=self.choice_round, player=self.player, selected_option=self.option)

        self.assert_integrity_error(
            RoundAnswer, round=self.choice_round, player=self.player, selected_option=self.option
        )

    def test_answer_cannot_have_both_option_and_numeric_value(self):
        self.assert_integrity_error(
            RoundAnswer,
            round=self.choice_round,
            player=self.player,
            selected_option=self.option,
            numeric_value=8,
        )

    def test_answer_must_be_consistent_with_its_round(self):
        other_game = Game.objects.create(created_by=self.guest)
        outsider = GamePlayer.objects.create(game=other_game, user=self.guest, player_order=1)
        invalid_answers = {
            "player from another game": (
                "player",
                {"round": self.choice_round, "player": outsider, "selected_option": self.option},
            ),
            "numeric value on choice round": (
                "numeric_value",
                {"round": self.choice_round, "player": self.player, "numeric_value": 8},
            ),
            "option on numeric round": (
                "selected_option",
                {"round": self.numeric_round, "player": self.player, "selected_option": self.option},
            ),
            "option from another question": (
                "selected_option",
                {"round": self.choice_round, "player": self.player, "selected_option": self.foreign_option},
            ),
        }
        for case, (field, fields) in invalid_answers.items():
            with self.subTest(case):
                with self.assertRaises(ValidationError) as context:
                    RoundAnswer(**fields).full_clean()
                self.assertIn(field, context.exception.message_dict)
