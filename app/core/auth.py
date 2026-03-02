"""Authentication dependencies and utilities."""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import verify_token

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    Extract and validate user ID from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        token = credentials.credentials
        payload = verify_token(token)
        
        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = int(payload["sub"])
        return user_id
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Get current authenticated user from database.
    
    Args:
        user_id: User ID from token
        session: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user not found or inactive
    """
    user_repo = UserRepository(session)
    user = await user_repo.get(id=user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify current user is a superuser.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_optional_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[int]:
    """
    Extract user ID from token if present, otherwise return None.
    Used for optional authentication endpoints.
    
    Args:
        credentials: Optional HTTP Bearer token credentials
        
    Returns:
        User ID if token is valid, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        
        if payload and "sub" in payload:
            return int(payload["sub"])
    except Exception:
        pass
    
    return None
