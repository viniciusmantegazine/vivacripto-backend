"""
Custom exceptions for the VivaCripto API.
Provides standardized error handling across the application.
"""
from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base exception for application errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: Any = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with id '{identifier}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class DuplicateError(AppException):
    """Resource already exists."""

    def __init__(self, resource: str, field: str, value: Any):
        detail = f"{resource} with {field} '{value}' already exists"
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class UnauthorizedError(AppException):
    """Authentication required or failed."""

    def __init__(self, detail: str = "Invalid or missing authentication credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(AppException):
    """Access denied."""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ServiceUnavailableError(AppException):
    """External service unavailable."""

    def __init__(self, service: str):
        detail = f"Service '{service}' is temporarily unavailable"
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
