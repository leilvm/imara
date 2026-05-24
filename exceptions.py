from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def imara_exception_handler(exc, context):
    """
    Return structured error envelopes for all API errors.

    Shape:
    {
        "error": {
            "code": "validation_error",
            "message": "Human-readable summary",
            "fields": { "field_name": ["error detail"] }   # validation only
        }
    }

    This consistent shape lets mobile clients parse errors without
    inspecting HTTP status codes alone.
    """
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # DRF validation errors have a dict or list body
    original_data = response.data

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        envelope = {
            "error": {
                "code": "validation_error",
                "message": "One or more fields failed validation.",
                "fields": original_data,
            }
        }
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        envelope = {
            "error": {
                "code": "authentication_required",
                "message": "Authentication credentials were not provided or are invalid.",
            }
        }
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        envelope = {
            "error": {
                "code": "permission_denied",
                "message": "You do not have permission to perform this action.",
            }
        }
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        envelope = {
            "error": {
                "code": "not_found",
                "message": "The requested resource was not found.",
            }
        }
    else:
        envelope = {
            "error": {
                "code": "api_error",
                "message": str(original_data),
            }
        }

    response.data = envelope
    return response