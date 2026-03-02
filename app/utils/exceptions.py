"""Custom HTTP exceptions for the application."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class SamscloakException(Exception):
    """Base exception for Samscloak application."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class DatabaseException(SamscloakException):
    """Database related exceptions."""
    pass


class OCRException(SamscloakException):
    """OCR processing exceptions."""
    pass


class AIServiceException(SamscloakException):
    """AI service related exceptions."""
    pass


class ValidationException(SamscloakException):
    """Data validation exceptions."""
    pass


class AuthenticationException(SamscloakException):
    """Authentication related exceptions."""
    pass


class AuthorizationException(SamscloakException):
    """Authorization related exceptions."""
    pass


class FileUploadException(SamscloakException):
    """File upload related exceptions."""
    pass


# HTTP Exception helpers
def create_http_exception(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> HTTPException:
    """Create a standardized HTTP exception."""
    return HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "details": details or {},
            "error_code": error_code
        }
    )


def bad_request_exception(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create a 400 Bad Request exception."""
    return create_http_exception(status.HTTP_400_BAD_REQUEST, message, details)


def unauthorized_exception(message: str = "Unauthorized") -> HTTPException:
    """Create a 401 Unauthorized exception."""
    return create_http_exception(status.HTTP_401_UNAUTHORIZED, message)


def forbidden_exception(message: str = "Forbidden") -> HTTPException:
    """Create a 403 Forbidden exception."""
    return create_http_exception(status.HTTP_403_FORBIDDEN, message)


def not_found_exception(resource: str, identifier: Any = None) -> HTTPException:
    """Create a 404 Not Found exception."""
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"
    return create_http_exception(status.HTTP_404_NOT_FOUND, message)


def conflict_exception(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create a 409 Conflict exception."""
    return create_http_exception(status.HTTP_409_CONFLICT, message, details)


def unprocessable_entity_exception(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create a 422 Unprocessable Entity exception."""
    return create_http_exception(status.HTTP_422_UNPROCESSABLE_ENTITY, message, details)


def internal_server_exception(message: str = "Internal server error") -> HTTPException:
    """Create a 500 Internal Server Error exception."""
    return create_http_exception(status.HTTP_500_INTERNAL_SERVER_ERROR, message)


def service_unavailable_exception(message: str = "Service temporarily unavailable") -> HTTPException:
    """Create a 503 Service Unavailable exception."""
    return create_http_exception(status.HTTP_503_SERVICE_UNAVAILABLE, message)
