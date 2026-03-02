"""Security utilities for API key management and input sanitization."""

import hashlib
import secrets
import re
from typing import Any, Dict, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return hash_api_key(api_key) == hashed_key


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize string input by removing potentially harmful characters."""
    if not text:
        return ""
    
    # Remove null bytes and control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove excessive whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Truncate if max_length is specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def sanitize_email(email: str) -> str:
    """Sanitize and validate email address."""
    if not email:
        return ""
    
    email = sanitize_string(email.lower().strip())
    
    # Basic email validation regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        return email
    
    return ""


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal."""
    if not filename:
        return ""
    
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Remove leading dots and slashes
    sanitized = sanitized.lstrip('./\\')
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized or "upload"


def validate_file_extension(filename: str, allowed_extensions: set[str]) -> bool:
    """Validate file extension against allowed set."""
    if not filename:
        return False
    
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return f".{extension}" in allowed_extensions


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data for logging purposes."""
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)
