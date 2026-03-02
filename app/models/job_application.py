"""Job application model definitions."""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from sqlmodel import SQLModel, Field, Column, Text
from sqlalchemy import JSON, DateTime


class ApplicationStatus(str, Enum):
    """Application status enumeration."""
    PENDING = "PENDING"
    ANALYZED = "ANALYZED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class JobApplicationBase(SQLModel):
    """Base job application model."""
    
    job_title: str = Field(max_length=255)
    company_name: str = Field(max_length=255)
    job_description: str = Field(sa_column=Column(Text))
    job_url: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=255)
    salary_range: Optional[str] = Field(default=None, max_length=100)
    remote_type: Optional[str] = Field(default=None, max_length=50)
    status: ApplicationStatus = Field(default=ApplicationStatus.PENDING)
    user_id: int = Field(foreign_key="users.id")


class JobApplication(JobApplicationBase, table=True):
    """Job application database model."""
    
    __tablename__ = "job_applications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    ai_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
    match_score: Optional[float] = Field(default=None, ge=0, le=100)
    missing_keywords: Optional[list[str]] = Field(
        default_factory=list,
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


class JobApplicationCreate(JobApplicationBase):
    """Job application creation schema."""
    raw_text: Optional[str] = None


class JobApplicationUpdate(SQLModel):
    """Job application update schema."""
    job_title: Optional[str] = Field(default=None, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    job_description: Optional[str] = None
    job_url: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=255)
    salary_range: Optional[str] = Field(default=None, max_length=100)
    remote_type: Optional[str] = Field(default=None, max_length=50)
    status: Optional[ApplicationStatus] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    match_score: Optional[float] = Field(default=None, ge=0, le=100)
    missing_keywords: Optional[list[str]] = None


class JobApplicationRead(JobApplicationBase):
    """Job application response schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    raw_text: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    match_score: Optional[float] = None
    missing_keywords: Optional[list[str]] = None
