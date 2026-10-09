from django.core.checks import Error, register
from django.core.exceptions import ValidationError

from .map import ADJACENCIES, TERRITORIES, validate_map


@register()
def check_project_map(app_configs, **kwargs):
    """Fail `manage.py check` (and so runserver and tests) when the project map is invalid."""
    try:
        validate_map(TERRITORIES, ADJACENCIES)
    except ValidationError as error:
        return [
            Error(message, hint="Fix TERRITORIES or ADJACENCIES in territories/map.py.", id="territories.E001")
            for message in error.messages
        ]
    return []
