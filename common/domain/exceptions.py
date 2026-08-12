from __future__ import annotations

from dataclasses import dataclass

from rest_framework import status


@dataclass(eq=False)
class DomainError(Exception):
    message: str = "The requested operation could not be completed."
    code: str = "domain_error"
    http_status: int = status.HTTP_400_BAD_REQUEST

    def __post_init__(self) -> None:
        super().__init__(self.message)


class NotFoundError(DomainError):
    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(message=message, code="not_found", http_status=status.HTTP_404_NOT_FOUND)


class PermissionDeniedError(DomainError):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message=message, code="permission_denied", http_status=status.HTTP_403_FORBIDDEN)


class ConflictError(DomainError):
    def __init__(self, message: str = "The request conflicts with the current resource state.") -> None:
        super().__init__(message=message, code="conflict", http_status=status.HTTP_409_CONFLICT)
