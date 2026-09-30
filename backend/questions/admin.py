from django.contrib import admin
from django.forms.models import BaseInlineFormSet

from .models import (
    ANSWER_OPTIONS_COUNT,
    AnswerOption,
    Category,
    ChoiceQuestion,
    NumericQuestion,
    validate_answer_options,
)


class AnswerOptionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        options = [
            form.instance
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        validate_answer_options(options)


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    formset = AnswerOptionInlineFormSet
    extra = 0
    min_num = ANSWER_OPTIONS_COUNT
    max_num = ANSWER_OPTIONS_COUNT
    validate_min = True
    validate_max = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ChoiceQuestion)
class ChoiceQuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerOptionInline]
    list_display = ("text", "category")
    list_filter = ("category",)
    list_select_related = ("category",)
    search_fields = ("text",)


@admin.register(NumericQuestion)
class NumericQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "category", "correct_answer")
    list_filter = ("category",)
    list_select_related = ("category",)
    search_fields = ("text",)
