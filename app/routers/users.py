"""API routes for user management."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.auth import get_current_user_id, get_current_user
from app.models.user import User, UserCreate, UserRead, UserUpdate
from app.repositories.user_repository import UserRepository
from app.utils.security import create_access_token
from app.utils.exceptions import DatabaseException, ValidationException

router = APIRouter()


async def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(session)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Register a new user account.
    
    - **email**: Valid email address (unique)
    - **password**: Password (min 8 characters)
    - **full_name**: Optional full name
    """
    try:
        # Check if user already exists
        existing_user = await user_repo.get_by_email(email=user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Create user
        user = await user_repo.create_user(user_data=user_data.dict())
        return user
        
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.post("/login")
async def login(
    email: str = Body(...),
    password: str = Body(...),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Authenticate user and return access token.
    
    - **email**: User email
    - **password**: User password
    """
    try:
        # Authenticate user
        user = await user_repo.authenticate(email=email, password=password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserRead.from_orm(user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Update current user profile."""
    try:
        updated_user = await user_repo.update(
            db_obj=current_user,
            obj_in=user_update.dict(exclude_unset=True)
        )
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.put("/me/resume")
async def update_master_resume(
    resume_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Update user's master resume.
    
    The master resume is used for AI analysis and tailoring.
    """
    try:
        await user_repo.update_master_resume(
            user_id=current_user.id,
            resume_data=resume_data
        )
        return {"message": "Master resume updated successfully"}
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Failed to update resume")


@router.put("/me/preferences")
async def update_preferences(
    preferences: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Update user preferences."""
    try:
        await user_repo.update_preferences(
            user_id=current_user.id,
            preferences=preferences
        )
        return {"message": "Preferences updated successfully"}
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Failed to update preferences")
