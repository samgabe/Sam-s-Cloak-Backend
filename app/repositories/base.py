"""Base repository class with common database operations."""

from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select, update, delete
from sqlmodel.sql.expression import SelectOfScalar

from app.utils.exceptions import DatabaseException

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            model: SQLModel class
            session: Async database session
        """
        self.model = model
        self.session = session
    
    async def create(self, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            obj_in: Dictionary with model data
            
        Returns:
            Created model instance
            
        Raises:
            DatabaseException: If creation fails
        """
        try:
            db_obj = self.model(**obj_in)
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.session.rollback()
            raise DatabaseException(f"Failed to create {self.model.__name__}: {str(e)}")
    
    async def get(self, *, id: int) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Model instance or None if not found
        """
        try:
            statement = select(self.model).where(self.model.id == id)
            result = await self.session.execute(statement)
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseException(f"Failed to get {self.model.__name__} with id {id}: {str(e)}")
    
    async def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field filters
            
        Returns:
            List of model instances
        """
        try:
            statement = select(self.model)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        statement = statement.where(getattr(self.model, field) == value)
            
            # Apply pagination
            statement = statement.offset(skip).limit(limit)
            
            result = await self.session.execute(statement)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseException(f"Failed to get multiple {self.model.__name__}: {str(e)}")
    
    async def update(
        self, 
        *, 
        db_obj: ModelType, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db_obj: Existing model instance
            obj_in: Dictionary with update data
            
        Returns:
            Updated model instance
            
        Raises:
            DatabaseException: If update fails
        """
        try:
            # Update model fields
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.session.rollback()
            raise DatabaseException(f"Failed to update {self.model.__name__}: {str(e)}")
    
    async def delete(self, *, id: int) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseException: If deletion fails
        """
        try:
            statement = delete(self.model).where(self.model.id == id)
            result = await self.session.execute(statement)
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            raise DatabaseException(f"Failed to delete {self.model.__name__}: {str(e)}")
    
    async def count(self, *, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering.
        
        Args:
            filters: Dictionary of field filters
            
        Returns:
            Number of matching records
        """
        try:
            from sqlalchemy import func
            
            statement = select(func.count(self.model.id))
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        statement = statement.where(getattr(self.model, field) == value)
            
            result = await self.session.execute(statement)
            return result.scalar()
        except Exception as e:
            raise DatabaseException(f"Failed to count {self.model.__name__}: {str(e)}")
    
    async def exists(self, *, filters: Dict[str, Any]) -> bool:
        """
        Check if a record exists with given filters.
        
        Args:
            filters: Dictionary of field filters
            
        Returns:
            True if record exists, False otherwise
        """
        try:
            statement = select(self.model.id).limit(1)
            
            for field, value in filters.items():
                if hasattr(self.model, field):
                    statement = statement.where(getattr(self.model, field) == value)
            
            result = await self.session.execute(statement)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            raise DatabaseException(f"Failed to check existence of {self.model.__name__}: {str(e)}")
    
    async def get_by_field(
        self, 
        *, 
        field_name: str, 
        field_value: Any
    ) -> Optional[ModelType]:
        """
        Get a record by field value.
        
        Args:
            field_name: Name of the field
            field_value: Value to search for
            
        Returns:
            Model instance or None if not found
        """
        try:
            if not hasattr(self.model, field_name):
                raise DatabaseException(f"Field {field_name} not found in {self.model.__name__}")
            
            statement = select(self.model).where(getattr(self.model, field_name) == field_value)
            result = await self.session.execute(statement)
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseException(f"Failed to get {self.model.__name__} by {field_name}: {str(e)}")
