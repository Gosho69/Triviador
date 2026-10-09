from django.contrib import admin
from django.core.exceptions import PermissionDenied

from games.models import GamePlayer

from .models import Capital, Territory


class OwnerListFilter(admin.RelatedOnlyFieldListFilter):
    """Owners present in the list, labelled with one query instead of one per player."""

    def field_choices(self, field, request, model_admin):
        owner_ids = model_admin.get_queryset(request).exclude(owner=None).values("owner_id")
        players = GamePlayer.objects.filter(pk__in=owner_ids).select_related("user")
        return [(player.pk, str(player)) for player in players]


class MapStructureAdmin(admin.ModelAdmin):
    """Territories and capitals are created by game initialization (M05), never by hand.

    They are removed only together with their game. Delete permission is kept so that deleting a
    Game in admin can cascade to them; only the direct delete UI is taken away.
    """

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), "show_delete": False}
        return super().change_view(request, object_id, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        raise PermissionDenied


@admin.register(Territory)
class TerritoryAdmin(MapStructureAdmin):
    list_display = ("name", "slug", "game", "owner", "score", "neighbor_names")
    list_filter = ("game", ("owner", OwnerListFilter))
    list_select_related = ("game", "owner__user")
    search_fields = ("name", "slug")
    fields = ("game", "name", "slug", "owner", "score", "neighbor_names")
    readonly_fields = ("game", "name", "slug", "owner", "neighbor_names")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("neighbors")

    @admin.display(description="Neighbors")
    def neighbor_names(self, obj):
        return ", ".join(sorted(neighbor.name for neighbor in obj.neighbors.all()))


@admin.register(Capital)
class CapitalAdmin(MapStructureAdmin):
    list_display = ("player", "territory", "health")
    list_filter = ("territory__game",)
    list_select_related = ("player__user", "territory")
    search_fields = ("player__user__username", "territory__name", "territory__slug")
    fields = ("player", "territory", "health")
    readonly_fields = ("player", "territory")
