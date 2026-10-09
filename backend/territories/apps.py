from django.apps import AppConfig


class TerritoriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'territories'

    def ready(self):
        from . import checks  # noqa: F401
