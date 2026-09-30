from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from questions.models import AnswerOption, Category, ChoiceQuestion, NumericQuestion


class CategoryTests(TestCase):
    def test_create_category_with_valid_name(self):
        category = Category.objects.create(name="История")

        category.full_clean()
        self.assertEqual(str(category), "История")

    def test_category_name_is_required(self):
        with self.assertRaises(ValidationError):
            Category(name="").full_clean()

    def test_category_name_is_unique(self):
        Category.objects.create(name="История")

        with self.assertRaises(ValidationError):
            Category(name="История").full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="История")


class ChoiceQuestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="География")

    def create_question(self, correct_flags):
        question = ChoiceQuestion.objects.create(
            category=self.category,
            text="Кой е най-високият връх в България?",
        )
        AnswerOption.objects.bulk_create(
            AnswerOption(question=question, text=f"Отговор {index}", is_correct=is_correct)
            for index, is_correct in enumerate(correct_flags, start=1)
        )
        return question

    def test_create_valid_choice_question(self):
        question = self.create_question([True, False, False, False])

        question.full_clean()
        self.assertEqual(question.category, self.category)
        self.assertEqual(question.answer_options.count(), 4)
        self.assertEqual(question.answer_options.filter(is_correct=True).count(), 1)
        self.assertIn(question, self.category.choicequestions.all())

    def test_invalid_choice_questions_fail_validation(self):
        invalid_cases = {
            "fewer than four options": [True, False, False],
            "more than four options": [True, False, False, False, False],
            "no correct option": [False, False, False, False],
            "more than one correct option": [True, True, False, False],
        }
        for case, correct_flags in invalid_cases.items():
            with self.subTest(case):
                question = self.create_question(correct_flags)
                with self.assertRaises(ValidationError):
                    question.full_clean()

    def test_text_is_required(self):
        with self.assertRaises(ValidationError):
            ChoiceQuestion(category=self.category, text="").full_clean()

    def test_deleting_question_deletes_its_answer_options(self):
        question = self.create_question([True, False, False, False])

        question.delete()

        self.assertFalse(AnswerOption.objects.exists())


class NumericQuestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="История")

    def test_create_valid_numeric_question(self):
        question = NumericQuestion.objects.create(
            category=self.category,
            text="През коя година е Освобождението на България?",
            correct_answer=1878,
        )

        question.full_clean()
        self.assertEqual(question.correct_answer, 1878)
        self.assertIn(question, self.category.numericquestions.all())

    def test_correct_answer_is_required(self):
        question = NumericQuestion(category=self.category, text="Колко области има България?")

        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_correct_answer_must_be_integer(self):
        question = NumericQuestion(
            category=self.category,
            text="Колко области има България?",
            correct_answer="двадесет и осем",
        )

        with self.assertRaises(ValidationError):
            question.full_clean()


class AnswerOptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Наука")
        cls.question = ChoiceQuestion.objects.create(
            category=category,
            text="Кой е химичният символ на златото?",
        )

    def test_is_correct_defaults_to_false(self):
        option = AnswerOption.objects.create(question=self.question, text="Ag")

        self.assertFalse(option.is_correct)

    def test_text_is_required(self):
        with self.assertRaises(ValidationError):
            AnswerOption(question=self.question, text="").full_clean()


class ProtectedCategoryTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Спорт")

    def test_category_with_choice_questions_cannot_be_deleted(self):
        ChoiceQuestion.objects.create(category=self.category, text="Въпрос")

        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_category_with_numeric_questions_cannot_be_deleted(self):
        NumericQuestion.objects.create(category=self.category, text="Въпрос", correct_answer=11)

        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_category_without_questions_can_be_deleted(self):
        self.category.delete()

        self.assertFalse(Category.objects.exists())
