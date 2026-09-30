from django.contrib import admin

from .models import Game, GamePlayer, Round, RoundAnswer


class GamePlayerInline(admin.TabularInline):
    model = GamePlayer
    extra = 0
    autocomplete_fields = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


class RoundAnswerInline(admin.TabularInline):
    model = RoundAnswer
    extra = 0
    raw_id_fields = ("player", "selected_option")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("player__user", "selected_option")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    inlines = [GamePlayerInline]
    list_display = ("id", "created_by", "status", "created_at", "started_at", "finished_at")
    list_filter = ("status",)
    list_select_related = ("created_by",)
    search_fields = ("created_by__username",)
    autocomplete_fields = ("created_by",)


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    inlines = [RoundAnswerInline]
    list_display = ("game", "number", "status", "question_type")
    list_filter = ("status", "question_type")
    list_select_related = ("game",)
    autocomplete_fields = ("game", "choice_question", "numeric_question")
