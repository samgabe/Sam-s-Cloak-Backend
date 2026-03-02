"""API routes for tailored documents."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.auth import get_current_user_id, get_current_user
from app.models.user import User
from app.models.tailored_document import (
    TailoredDocument,
    TailoredDocumentCreate,
    TailoredDocumentRead,
    DocumentType
)
from app.repositories.tailored_document_repository import TailoredDocumentRepository
from app.utils.exceptions import DatabaseException

router = APIRouter()


async def get_document_repo(session: AsyncSession = Depends(get_session)) -> TailoredDocumentRepository:
    """Get tailored document repository instance."""
    return TailoredDocumentRepository(session)


@router.post("/documents", response_model=TailoredDocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: TailoredDocumentCreate,
    current_user: User = Depends(get_current_user),
    document_repo: TailoredDocumentRepository = Depends(get_document_repo)
):
    """
    Create a new tailored document.
    
    - **title**: Document title
    - **content**: Document content (Markdown)
    - **document_type**: Type (RESUME, COVER_LETTER, THANK_YOU)
    - **job_application_id**: Associated job application
    """
    try:
        # Verify user owns the application (add check here)
        document = await document_repo.create(obj_in=document_data.dict())
        return document
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Failed to create document")


@router.get("/documents", response_model=List[TailoredDocumentRead])
async def get_user_documents(
    document_type: Optional[DocumentType] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    document_repo: TailoredDocumentRepository = Depends(get_document_repo)
):
    """Get user's tailored documents with optional filtering."""
    try:
        documents = await document_repo.get_by_user_id(
            user_id=current_user.id,
            document_type=document_type,
            skip=skip,
            limit=limit
        )
        return documents
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Failed to get documents")


@router.get("/documents/{document_id}", response_model=TailoredDocumentRead)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    document_repo: TailoredDocumentRepository = Depends(get_document_repo)
):
    """Get a specific tailored document."""
    try:
        document = await document_repo.get(id=document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.get("/applications/{application_id}/documents", response_model=List[TailoredDocumentRead])
async def get_application_documents(
    application_id: int,
    document_type: Optional[DocumentType] = Query(None),
    current_user: User = Depends(get_current_user),
    document_repo: TailoredDocumentRepository = Depends(get_document_repo)
):
    """Get all documents for a specific job application."""
    try:
        documents = await document_repo.get_by_application_id(
            application_id=application_id,
            document_type=document_type
        )
        return documents
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Failed to get documents")


@router.get("/applications/{application_id}/documents/latest", response_model=TailoredDocumentRead)
async def get_latest_document(
    application_id: int,
    document_type: DocumentType,
    current_user: User = Depends(get_current_user),
    document_repo: TailoredDocumentRepository = Depends(get_document_repo)
):
    """Get the latest version of a document for an application."""
    try:
        document = await document_repo.get_latest_version(
            application_id=application_id,
            document_type=document_type
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    document_repo: TailoredDocumentRepository = Depends(get_document_repo)
):
    """Deactivate a tailored document."""
    try:
        document = await document_repo.get(id=document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        await document_repo.deactivate_document(document_id=document_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to deactivate document")


@router.get("/documents/statistics")
async def get_document_statistics(
    current_user: User = Depends(get_current_user),
    document_repo: TailoredDocumentRepository = Depends(get_document_repo)
):
    """Get document statistics for the user."""
    try:
        statistics = await document_repo.get_document_statistics(user_id=current_user.id)
        return statistics
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Failed to get statistics")
