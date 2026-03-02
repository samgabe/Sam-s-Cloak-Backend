"""Tailored document repository with specific document operations."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_

from app.models.tailored_document import TailoredDocument, DocumentType
from app.repositories.base import BaseRepository
from app.utils.exceptions import DatabaseException


class TailoredDocumentRepository(BaseRepository[TailoredDocument]):
    """Repository for TailoredDocument model operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize tailored document repository."""
        super().__init__(TailoredDocument, session)
    
    async def get_by_application_id(
        self, 
        *, 
        application_id: int,
        document_type: Optional[DocumentType] = None
    ) -> List[TailoredDocument]:
        """
        Get documents for a specific job application.
        
        Args:
            application_id: Job application ID
            document_type: Optional document type filter
            
        Returns:
            List of tailored document instances
        """
        try:
            filters = {"job_application_id": application_id}
            if document_type:
                filters["document_type"] = document_type
            
            return await self.get_multi(filters=filters)
        except DatabaseException:
            raise
    
    async def get_by_user_id(
        self, 
        *, 
        user_id: int,
        document_type: Optional[DocumentType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TailoredDocument]:
        """
        Get documents for a specific user.
        
        Args:
            user_id: User ID
            document_type: Optional document type filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tailored document instances
        """
        try:
            filters = {"user_id": user_id}
            if document_type:
                filters["document_type"] = document_type
            
            return await self.get_multi(skip=skip, limit=limit, filters=filters)
        except DatabaseException:
            raise
    
    async def get_latest_version(
        self, 
        *, 
        application_id: int,
        document_type: DocumentType
    ) -> Optional[TailoredDocument]:
        """
        Get the latest version of a document for an application.
        
        Args:
            application_id: Job application ID
            document_type: Document type
            
        Returns:
            Latest document instance or None
        """
        try:
            statement = select(TailoredDocument).where(
                and_(
                    TailoredDocument.job_application_id == application_id,
                    TailoredDocument.document_type == document_type,
                    TailoredDocument.is_active == True
                )
            )
            statement = statement.order_by(TailoredDocument.version.desc())
            statement = statement.limit(1)
            
            result = await self.session.execute(statement)
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseException(f"Failed to get latest document version: {str(e)}")
    
    async def create_new_version(
        self, 
        *, 
        application_id: int,
        user_id: int,
        document_type: DocumentType,
        title: str,
        content: str,
        doc_metadata: Optional[Dict[str, Any]] = None
    ) -> TailoredDocument:
        """
        Create a new version of a document.
        
        Args:
            application_id: Job application ID
            user_id: User ID
            document_type: Document type
            title: Document title
            content: Document content
            doc_metadata: Optional metadata
            
        Returns:
            Created document instance
        """
        try:
            # Get latest version to increment
            latest_doc = await self.get_latest_version(
                application_id=application_id,
                document_type=document_type
            )
            
            next_version = 1
            if latest_doc:
                # Deactivate previous version
                await self.update(db_obj=latest_doc, obj_in={"is_active": False})
                next_version = latest_doc.version + 1
            
            # Create new version
            document_data = {
                "title": title,
                "content": content,
                "document_type": document_type,
                "job_application_id": application_id,
                "user_id": user_id,
                "version": next_version,
                "doc_metadata": doc_metadata or {},
                "is_active": True
            }
            
            return await self.create(obj_in=document_data)
        except DatabaseException:
            raise
    
    async def get_document_history(
        self, 
        *, 
        application_id: int,
        document_type: DocumentType
    ) -> List[TailoredDocument]:
        """
        Get all versions of a document for an application.
        
        Args:
            application_id: Job application ID
            document_type: Document type
            
        Returns:
            List of document instances ordered by version
        """
        try:
            statement = select(TailoredDocument).where(
                and_(
                    TailoredDocument.job_application_id == application_id,
                    TailoredDocument.document_type == document_type
                )
            )
            statement = statement.order_by(TailoredDocument.version.desc())
            
            result = await self.session.execute(statement)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseException(f"Failed to get document history: {str(e)}")
    
    async def get_active_documents(
        self, 
        *, 
        user_id: int,
        document_type: Optional[DocumentType] = None
    ) -> List[TailoredDocument]:
        """
        Get all active documents for a user.
        
        Args:
            user_id: User ID
            document_type: Optional document type filter
            
        Returns:
            List of active document instances
        """
        try:
            filters = {"user_id": user_id, "is_active": True}
            if document_type:
                filters["document_type"] = document_type
            
            return await self.get_multi(filters=filters)
        except DatabaseException:
            raise
    
    async def deactivate_document(self, *, document_id: int) -> TailoredDocument:
        """
        Deactivate a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Updated document instance
        """
        try:
            document = await self.get(id=document_id)
            if not document:
                raise DatabaseException(f"Document with id {document_id} not found")
            
            return await self.update(db_obj=document, obj_in={"is_active": False})
        except DatabaseException:
            raise
    
    async def update_content(
        self, 
        *, 
        document_id: int,
        content: str,
        doc_metadata: Optional[Dict[str, Any]] = None
    ) -> TailoredDocument:
        """
        Update document content and metadata.
        
        Args:
            document_id: Document ID
            content: New content
            doc_metadata: Optional metadata
            
        Returns:
            Updated document instance
        """
        try:
            document = await self.get(id=document_id)
            if not document:
                raise DatabaseException(f"Document with id {document_id} not found")
            
            update_data = {"content": content}
            if doc_metadata is not None:
                update_data["doc_metadata"] = doc_metadata
            
            return await self.update(db_obj=document, obj_in=update_data)
        except DatabaseException:
            raise
    
    async def get_document_statistics(self, *, user_id: int) -> Dict[str, Any]:
        """
        Get document statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with document statistics
        """
        try:
            from sqlalchemy import func
            
            # Count by document type
            type_counts = await self.session.execute(
                select(
                    TailoredDocument.document_type,
                    func.count(TailoredDocument.id).label('count')
                ).where(
                    and_(
                        TailoredDocument.user_id == user_id,
                        TailoredDocument.is_active == True
                    )
                )
                .group_by(TailoredDocument.document_type)
            )
            
            type_stats = {doc_type: count for doc_type, count in type_counts.all()}
            
            # Total documents
            total_count = await self.count(filters={"user_id": user_id, "is_active": True})
            
            return {
                "total_documents": total_count,
                "type_breakdown": type_stats,
                "resumes": type_stats.get(DocumentType.RESUME, 0),
                "cover_letters": type_stats.get(DocumentType.COVER_LETTER, 0),
                "thank_you_notes": type_stats.get(DocumentType.THANK_YOU, 0)
            }
        except Exception as e:
            raise DatabaseException(f"Failed to get document statistics: {str(e)}")
