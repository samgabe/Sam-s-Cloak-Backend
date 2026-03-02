"""User model definitions."""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, DateTime

class UserBase(SQLModel):
    """Base user model with common fields."""
    
    email: str = Field(index=True, unique=True, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class User(UserBase, table=True):
    """User database model."""
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)
    master_resume: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
    preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow)
    )


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(min_length=8, max_length=72)  # Max 72 bytes for bcrypt compatibility


class UserUpdate(SQLModel):
    """User update schema."""
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = Field(default=None)
    master_resume: Optional[Dict[str, Any]] = Field(default=None)
    preferences: Optional[Dict[str, Any]] = Field(default=None)


class UserRead(UserBase):
    """User response schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    master_resume: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
