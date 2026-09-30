from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from games.models import Game, GamePlayer, Round, RoundAnswer
from questions.models import AnswerOption, Category, ChoiceQuestion, NumericQuestion

User = get_user_model()


class GameModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.com", password="Str0ng-pass-123"
        )
        cls.guest = User.objects.create_user(
            username="guest", email="guest@example.com", password="Str0ng-pass-123"
        )
        category = Category.objects.create(name="История")
        cls.choice_question = ChoiceQuestion.objects.create(
            category=category, text="Кой хан основава Дунавска България?"
        )
        cls.correct_option = AnswerOption.objects.create(
            question=cls.choice_question, text="Аспарух", is_correct=True
        )
        cls.numeric_question = NumericQuestion.objects.create(
            category=category, text="През коя година е Освобождението?", correct_answer=1878
        )

    def setUp(self):
        self.game = Game.objects.create(created_by=self.host)
        self.host_player = GamePlayer.objects.create(game=self.game, user=self.host, player_order=1)
        self.guest_player = GamePlayer.objects.create(game=self.game, user=self.guest, player_order=2)
        self.choice_round = Round.objects.create(
            game=self.game,
            number=1,
            question_type=Round.CHOICE,
            choice_question=self.choice_question,
        )
        self.numeric_round = Round.objects.create(
            game=self.game,
            number=2,
            question_type=Round.NUMERIC,
            numeric_question=self.numeric_question,
        )

    def test_new_game_is_waiting_and_not_started(self):
        self.assertEqual(self.game.status, Game.WAITING)
        self.assertIsNotNone(self.game.created_at)
        self.assertIsNone(self.game.started_at)
        self.assertIsNone(self.game.finished_at)
        self.assertIn(self.game, self.host.created_games.all())

    def test_new_player_starts_active_with_zero_score(self):
        self.assertEqual(self.host_player.score, 0)
        self.assertTrue(self.host_player.is_active)
        self.assertIsNotNone(self.host_player.joined_at)
        self.assertIn(self.host_player, self.host.game_players.all())

    def test_players_are_ordered_by_player_order(self):
        GamePlayer.objects.filter(pk=self.host_player.pk).update(player_order=3)

        self.assertEqual(list(self.game.players.all()), [self.guest_player, self.host_player])

    def test_rounds_are_ordered_by_number(self):
        self.choice_round.number = 3
        self.choice_round.save()

        self.assertEqual(list(self.game.rounds.all()), [self.numeric_round, self.choice_round])

    def test_new_round_is_pending(self):
        self.assertEqual(self.choice_round.status, Round.PENDING)
        self.assertIsNone(self.choice_round.started_at)
        self.assertIsNone(self.choice_round.finished_at)

    def test_round_question_returns_question_of_its_type(self):
        self.assertEqual(self.choice_round.question, self.choice_question)
        self.assertEqual(self.numeric_round.question, self.numeric_question)
        self.assertIn(self.choice_round, self.choice_question.rounds.all())
        self.assertIn(self.numeric_round, self.numeric_question.rounds.all())

    def test_choice_answer_links_round_player_and_option(self):
        answer = RoundAnswer.objects.create(
            round=self.choice_round,
            player=self.host_player,
            selected_option=self.correct_option,
        )

        answer.full_clean()
        self.assertIsNone(answer.is_correct)
        self.assertEqual(answer.points_awarded, 0)
        self.assertIn(answer, self.choice_round.answers.all())
        self.assertIn(answer, self.host_player.answers.all())
        self.assertIn(answer, self.correct_option.round_answers.all())

    def test_numeric_answer_stores_value(self):
        answer = RoundAnswer.objects.create(
            round=self.numeric_round,
            player=self.guest_player,
            numeric_value=1878,
        )

        answer.full_clean()
        self.assertEqual(answer.numeric_value, 1878)
        self.assertIsNone(answer.selected_option)

    def test_deleting_game_deletes_players_rounds_and_answers(self):
        RoundAnswer.objects.create(round=self.numeric_round, player=self.host_player, numeric_value=1)

        self.game.delete()

        self.assertFalse(GamePlayer.objects.exists())
        self.assertFalse(Round.objects.exists())
        self.assertFalse(RoundAnswer.objects.exists())

    def test_deleting_player_deletes_their_answers(self):
        RoundAnswer.objects.create(round=self.numeric_round, player=self.guest_player, numeric_value=1)

        self.guest_player.delete()

        self.assertFalse(RoundAnswer.objects.exists())

    def test_protected_references_cannot_be_deleted(self):
        RoundAnswer.objects.create(
            round=self.choice_round,
            player=self.host_player,
            selected_option=self.correct_option,
        )
        protected = {
            "game creator": self.host,
            "player user": self.guest,
            "choice question in a round": self.choice_question,
            "numeric question in a round": self.numeric_question,
            "selected answer option": self.correct_option,
        }
        for case, instance in protected.items():
            with self.subTest(case), self.assertRaises(ProtectedError):
                instance.delete()
