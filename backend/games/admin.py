from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.forms.models import BaseInlineFormSet
from django.utils import timezone

from .models import Game, GamePlayer, Round, RoundAnswer
from .services import PLAYERS_COUNT, initialize_game


class GamePlayerFormSet(BaseInlineFormSet):
    """Server-side guard for the players inline; the permissions below only shape the form.

    The game's status is re-read from the database, so a form opened before the game started
    cannot change its players afterwards.
    """

    def clean(self):
        super().clean()
        if not self.has_changed():
            return

        game = self.instance
        if game.pk and Game.objects.filter(pk=game.pk).exclude(status=Game.WAITING).exists():
            raise ValidationError("Players cannot be changed after the game has started.")

        kept = [
            form
            for form in self.forms
            if not self._should_delete_form(form) and (form.instance.pk or form.has_changed())
        ]
        if len(kept) > PLAYERS_COUNT:
            raise ValidationError(f"A game can have at most {PLAYERS_COUNT} players.")


class GamePlayerInline(admin.TabularInline):
    model = GamePlayer
    formset = GamePlayerFormSet
    extra = 0
    max_num = PLAYERS_COUNT
    autocomplete_fields = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    # Players are fixed once a game has started (`obj` is the parent game).
    def has_add_permission(self, request, obj=None):
        return self._is_waiting(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._is_waiting(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._is_waiting(obj) and super().has_delete_permission(request, obj)

    @staticmethod
    def _is_waiting(game):
        return game is None or game.status == Game.WAITING


class RoundAnswerInline(admin.TabularInline):
    model = RoundAnswer
    extra = 0
    raw_id_fields = ("player", "selected_option")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("player__user", "selected_option")


class GameAdminForm(forms.ModelForm):
    # A game starts only through initialization; by hand it can only be finished or cancelled.
    MANUAL_STATUSES = (Game.FINISHED, Game.CANCELLED)

    class Meta:
        model = Game
        fields = "__all__"

    def clean_status(self):
        status = self.cleaned_data["status"]
        if "status" in self.changed_data and status not in self.MANUAL_STATUSES:
            raise ValidationError(
                "The status can only be changed to Finished or Cancelled here; "
                "use the “Initialize selected games” action to start a game."
            )
        return status


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameAdminForm
    inlines = [GamePlayerInline]
    list_display = ("id", "created_by", "status", "created_at", "started_at", "finished_at")
    list_filter = ("status",)
    list_select_related = ("created_by",)
    search_fields = ("created_by__username",)
    autocomplete_fields = ("created_by",)
    readonly_fields = ("started_at", "finished_at")
    actions = ["initialize_games"]

    def save_model(self, request, obj, form, change):
        if "status" in form.changed_data and obj.status in GameAdminForm.MANUAL_STATUSES:
            obj.finished_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description="Initialize selected games (build map, assign capitals, start)")
    def initialize_games(self, request, queryset):
        # Each game is initialized in its own transaction, so one failure does not hide or undo the others.
        for game in queryset:
            try:
                initialize_game(game)
            except ValidationError as error:
                self.message_user(request, f"{game}: {' '.join(error.messages)}", messages.ERROR)
            except DatabaseError as error:
                self.message_user(request, f"{game}: database error, nothing was changed ({error}).", messages.ERROR)
            else:
                self.message_user(request, f"{game} initialized.", messages.SUCCESS)


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    inlines = [RoundAnswerInline]
    list_display = ("game", "number", "status", "question_type")
    list_filter = ("status", "question_type")
    list_select_related = ("game",)
    autocomplete_fields = ("game", "choice_question", "numeric_question")
