import re

from django.test import TestCase

from questions.models import (
    ANSWER_OPTIONS_COUNT,
    AnswerOption,
    Category,
    ChoiceQuestion,
    NumericQuestion,
)

CYRILLIC = re.compile(r"[А-Яа-я]")


class QuestionBankFixtureTests(TestCase):
    fixtures = ["questions/question_bank.json"]

    def test_fixture_loads_expected_counts(self):
        self.assertEqual(Category.objects.count(), 6)
        self.assertEqual(ChoiceQuestion.objects.count(), 12)
        self.assertEqual(AnswerOption.objects.count(), 48)
        self.assertEqual(NumericQuestion.objects.count(), 12)

    def test_every_choice_question_has_four_options_and_one_correct(self):
        for question in ChoiceQuestion.objects.prefetch_related("answer_options"):
            with self.subTest(question=question.pk):
                options = question.answer_options.all()
                self.assertEqual(len(options), ANSWER_OPTIONS_COUNT)
                self.assertEqual(sum(option.is_correct for option in options), 1)
                question.full_clean()

    def test_every_numeric_question_has_integer_correct_answer(self):
        for question in NumericQuestion.objects.all():
            with self.subTest(question=question.pk):
                self.assertIsInstance(question.correct_answer, int)
                question.full_clean()

    def test_questions_are_in_bulgarian(self):
        texts = [
            *Category.objects.values_list("name", flat=True),
            *ChoiceQuestion.objects.values_list("text", flat=True),
            *NumericQuestion.objects.values_list("text", flat=True),
        ]
        for text in texts:
            with self.subTest(text=text):
                self.assertRegex(text, CYRILLIC)
