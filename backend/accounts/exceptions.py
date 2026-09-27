from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Wrap every DRF error response in a single `{"errors": {field: [messages]}}` shape."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    # Read response.data, not exc: DRF converts Django's Http404/PermissionDenied
    # into API exceptions only for the response it builds.
    if isinstance(exc, ValidationError) or not isinstance(response.data, dict) or "detail" not in response.data:
        errors = _as_field_errors(response.data)
    else:
        errors = {"detail": [str(response.data["detail"])]}

    response.data = {"errors": errors}
    return response


def _as_field_errors(data):
    if isinstance(data, dict):
        return {
            field: messages if isinstance(messages, list) else [messages]
            for field, messages in data.items()
        }
    messages = data if isinstance(data, list) else [data]
    return {api_settings.NON_FIELD_ERRORS_KEY: messages}
