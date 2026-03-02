"""Tailored document model definitions."""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from sqlmodel import SQLModel, Field, Column, Text
from sqlalchemy import JSON, DateTime


class DocumentType(str, Enum):
    """Document type enumeration."""
    RESUME = "RESUME"
    COVER_LETTER = "COVER_LETTER"
    THANK_YOU = "THANK_YOU"


class TailoredDocumentBase(SQLModel):
    """Base tailored document model."""
    
    title: str = Field(max_length=255)
    content: str = Field(sa_column=Column(Text))
    document_type: DocumentType
    job_application_id: int = Field(foreign_key="job_applications.id")
    user_id: int = Field(foreign_key="users.id")


class TailoredDocument(TailoredDocumentBase, table=True):
    """Tailored document database model."""
    
    __tablename__ = "tailored_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    doc_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON)  # Column name in DB is still "metadata"
    )
    version: int = Field(default=1)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow)
    )


class TailoredDocumentCreate(TailoredDocumentBase):
    """Tailored document creation schema."""
    doc_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TailoredDocumentUpdate(SQLModel):
    """Tailored document update schema."""
    title: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = None
    document_type: Optional[DocumentType] = None
    doc_metadata: Optional[Dict[str, Any]] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None


class TailoredDocumentRead(TailoredDocumentBase):
    """Tailored document response schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    doc_metadata: Optional[Dict[str, Any]] = None
    version: int
    is_active: bool
