from django.urls import path

from . import views

app_name = "games"

urlpatterns = [
    path("", views.GameListView.as_view(), name="list"),
    path("<int:pk>/", views.GameDetailView.as_view(), name="detail"),
    path("<int:pk>/join/", views.JoinGameView.as_view(), name="join"),
    path("<int:pk>/leave/", views.LeaveGameView.as_view(), name="leave"),
    path("<int:pk>/start/", views.StartGameView.as_view(), name="start"),
    path("<int:pk>/cancel/", views.CancelGameView.as_view(), name="cancel"),
]
