from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _flatten(data):
    """Turn DRF error structures into one readable sentence."""
    if isinstance(data, dict):
        parts = []
        for key, value in data.items():
            text = _flatten(value)
            parts.append(text if key in ("non_field_errors", "detail") else f"{key}: {text}")
        return " ".join(parts)
    if isinstance(data, (list, tuple)):
        return " ".join(_flatten(item) for item in data)
    return str(data)


def custom_exception_handler(exc, context):
    """
    Consistent error body for every failure:

        {"detail": "<human readable message>", "errors": {...field errors, when any...}}
    """
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "This record cannot be deleted because other records (for example orders) depend on it."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(detail=exc.message_dict if hasattr(exc, "error_dict") else exc.messages)

    response = exception_handler(exc, context)
    if response is None:
        return None  # unexpected errors -> Django's 500 handling

    data = response.data
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        return response
    response.data = {"detail": _flatten(data), "errors": data}
    return response
