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


# =============================================================================
# HTTP Exceptions (4xx, 5xx)
# =============================================================================


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


class RateLimitExceededError(AppException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


# =============================================================================
# Domain-Specific Exceptions (for internal use, can be caught and converted)
# =============================================================================


class DomainException(Exception):
    """Base exception for domain/business logic errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.context = context or {}
        super().__init__(message)


class ContentGenerationError(DomainException):
    """Error during AI content generation."""

    def __init__(self, message: str, source_title: Optional[str] = None):
        context = {"source_title": source_title} if source_title else {}
        super().__init__(message, context)


class ImageGenerationError(DomainException):
    """Error during AI image generation."""

    def __init__(self, message: str, article_title: Optional[str] = None):
        context = {"article_title": article_title} if article_title else {}
        super().__init__(message, context)


class DeduplicationError(DomainException):
    """Error during duplicate detection."""

    def __init__(self, message: str, news_title: Optional[str] = None):
        context = {"news_title": news_title} if news_title else {}
        super().__init__(message, context)


class NewsCollectionError(DomainException):
    """Error during news collection from sources."""

    def __init__(self, message: str, source: Optional[str] = None):
        context = {"source": source} if source else {}
        super().__init__(message, context)


class PublishingError(DomainException):
    """Error during article publishing."""

    def __init__(self, message: str, article_title: Optional[str] = None):
        context = {"article_title": article_title} if article_title else {}
        super().__init__(message, context)


class DailyLimitReachedError(DomainException):
    """Daily post limit has been reached."""

    def __init__(self, limit: int, current_count: int):
        message = f"Daily post limit of {limit} reached (current: {current_count})"
        super().__init__(message, {"limit": limit, "current_count": current_count})


class QualityValidationError(DomainException):
    """Article failed quality validation."""

    def __init__(self, message: str, validation_errors: Optional[list] = None):
        context = {"validation_errors": validation_errors} if validation_errors else {}
        super().__init__(message, context)


class ExternalAPIError(DomainException):
    """Error communicating with external API."""

    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        context = {"service": service}
        if status_code:
            context["status_code"] = status_code
        super().__init__(f"{service}: {message}", context)
