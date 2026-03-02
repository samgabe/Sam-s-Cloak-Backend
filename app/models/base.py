"""Base model definitions."""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Column, DateTime
from sqlmodel import Field


class TimestampMixin:
    """Mixin for timestamp fields. Don't inherit from SQLModel to avoid conflicts."""
    
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow)
    )

class JSONBMixin:
    """Mixin for JSONB fields."""
    
    def dict_with_jsonb(self, **kwargs) -> Dict[str, Any]:
        """Convert model to dict with proper JSONB serialization."""
        data = self.dict(**kwargs) if hasattr(self, 'dict') else {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = value
        return data
