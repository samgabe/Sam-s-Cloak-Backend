"""User repository with specific user operations."""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.utils.exceptions import DatabaseException


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize user repository."""
        super().__init__(User, session)
    
    async def get_by_email(self, *, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User instance or None if not found
        """
        try:
            return await self.get_by_field(field_name="email", field_value=email)
        except DatabaseException:
            raise
    
    async def create_user(self, *, user_data: Dict[str, Any]) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            user_data: User creation data including password
            
        Returns:
            Created user instance
        """
        try:
            from app.utils.security import hash_password
            
            # Hash password before storing
            if "password" in user_data:
                user_data["hashed_password"] = hash_password(user_data.pop("password"))
            
            return await self.create(obj_in=user_data)
        except DatabaseException:
            raise
    
    async def authenticate(self, *, email: str, password: str) -> Optional[User]:
        """
        Authenticate user by email and password.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Authenticated user or None if authentication fails
        """
        try:
            from app.utils.security import verify_password
            
            user = await self.get_by_email(email=email)
            if not user:
                return None
            
            if not verify_password(password, user.hashed_password):
                return None
            
            return user
        except Exception as e:
            raise DatabaseException(f"Authentication failed: {str(e)}")
    
    async def update_master_resume(self, *, user_id: int, resume_data: Dict[str, Any]) -> User:
        """
        Update user's master resume.
        
        Args:
            user_id: User ID
            resume_data: Resume data to store
            
        Returns:
            Updated user instance
        """
        try:
            user = await self.get(id=user_id)
            if not user:
                raise DatabaseException(f"User with id {user_id} not found")
            
            return await self.update(db_obj=user, obj_in={"master_resume": resume_data})
        except DatabaseException:
            raise
    
    async def update_preferences(self, *, user_id: int, preferences: Dict[str, Any]) -> User:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            preferences: User preferences data
            
        Returns:
            Updated user instance
        """
        try:
            user = await self.get(id=user_id)
            if not user:
                raise DatabaseException(f"User with id {user_id} not found")
            
            # Merge with existing preferences
            updated_preferences = user.preferences or {}
            updated_preferences.update(preferences)
            
            return await self.update(db_obj=user, obj_in={"preferences": updated_preferences})
        except DatabaseException:
            raise
    
    async def get_active_users(self, *, skip: int = 0, limit: int = 100):
        """
        Get active users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active user instances
        """
        return await self.get_multi(skip=skip, limit=limit, filters={"is_active": True})
    
    async def deactivate_user(self, *, user_id: int) -> User:
        """
        Deactivate a user account.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user instance
        """
        try:
            user = await self.get(id=user_id)
            if not user:
                raise DatabaseException(f"User with id {user_id} not found")
            
            return await self.update(db_obj=user, obj_in={"is_active": False})
        except DatabaseException:
            raise
