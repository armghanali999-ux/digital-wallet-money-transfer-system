from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from common.domain.exceptions import DomainError


def domain_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response(
            {"success": False, "error": {"code": exc.code, "message": exc.message}},
            status=exc.http_status,
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    response.data = {
        "success": False,
        "error": {
            "code": "request_error",
            "message": "The request could not be processed.",
            "details": response.data,
        },
    }
    return response
