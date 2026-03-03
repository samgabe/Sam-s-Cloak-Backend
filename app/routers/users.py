"""API routes for user management."""

from datetime import datetime
from enum import Enum
from io import BytesIO
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Body, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User, UserCreate, UserRead, UserUpdate
from app.repositories.user_repository import UserRepository
from app.services.document_export_service import (
    DocumentExportService,
    TemplateStyle,
    ExportFormat,
)
from app.utils.security import create_access_token
from app.utils.exceptions import DatabaseException, ValidationException

router = APIRouter()


async def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(session)


def get_export_service() -> DocumentExportService:
    """Get document export service instance."""
    return DocumentExportService()


class TemplateStyleQuery(str, Enum):
    """Query-friendly template style enum for resume export."""

    ATS = "ats"
    MODERN = "modern"


class ExportFormatQuery(str, Enum):
    """Query-friendly export format enum for resume export."""

    PDF = "pdf"
    DOCX = "docx"


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


@router.post("/me/resume/upload")
async def upload_master_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Upload and parse a resume file.
    
    Supports PDF, DOCX, and image files. Extracts text content using OCR/PDF parsing
    and stores it as the user's master resume along with template information.
    """
    try:
        # Validate file type
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
            "image/png", "image/jpeg", "image/webp"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.content_type}. Supported types: PDF, DOCX, PNG, JPG, WebP"
            )
        
        # Validate file size (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 10MB"
            )
        
        # Extract text from file
        template_info = None
        if file.content_type == "application/pdf":
            text_content = await extract_pdf_text(file_content)
            # Extract template information from PDF
            from app.services.pdf_service import PDFService
            pdf_service = PDFService()
            template_info = await pdf_service.extract_template_info(file_content)
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text_content = await extract_docx_text(file_content)
        else:  # Image files
            text_content = await extract_image_text(file_content)
        
        # Store as master resume with template info
        resume_data = {
            "text": text_content,
            "filename": file.filename,
            "content_type": file.content_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "template": template_info  # Store template styling information
        }
        
        await user_repo.update_master_resume(
            user_id=current_user.id,
            resume_data=resume_data
        )
        
        return {
            "message": "Resume uploaded successfully",
            "filename": file.filename,
            "content_length": len(text_content),
            "has_template": template_info is not None,
            "preview": text_content[:500] + "..." if len(text_content) > 500 else text_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")


async def extract_pdf_text(file_content: bytes) -> str:
    """Extract text from PDF file."""
    try:
        import PyPDF2
        from io import BytesIO
        
        pdf_file = BytesIO(file_content)
        reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


async def extract_docx_text(file_content: bytes) -> str:
    """Extract text from DOCX file."""
    try:
        import docx
        from io import BytesIO
        
        doc_file = BytesIO(file_content)
        doc = docx.Document(doc_file)
        
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        raise Exception(f"DOCX extraction failed: {str(e)}")


async def extract_image_text(file_content: bytes) -> str:
    """Extract text from image file using OCR."""
    try:
        import pytesseract
        from PIL import Image
        from io import BytesIO
        
        image = Image.open(BytesIO(file_content))
        
        # Configure tesseract path if needed
        if hasattr(pytesseract, 'pytesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR extraction failed: {str(e)}")


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


@router.get("/me/resume/export")
async def export_master_resume(
    fmt: ExportFormatQuery = Query(ExportFormatQuery.PDF, alias="format"),
    template: TemplateStyleQuery = Query(TemplateStyleQuery.ATS),
    current_user: User = Depends(get_current_user),
    export_service: DocumentExportService = Depends(get_export_service),
):
    """
    Export the user's master resume as a DOCX or PDF.

    - **format**: `pdf` or `docx`
    - **template**: `ats` (simple, ATS-friendly) or `modern`
    """
    if not current_user.master_resume:
        raise HTTPException(
            status_code=400,
            detail="Master resume not found. Upload it first via /users/me/resume or /users/me/resume/upload.",
        )

    resume_data = current_user.master_resume
    content = None
    title = "Resume"

    if isinstance(resume_data, dict):
        for key in ("text", "content", "resume_text", "body"):
            if key in resume_data and isinstance(resume_data[key], str):
                content = resume_data[key]
                break
        if resume_data.get("filename"):
            title = resume_data["filename"]
    else:
        content = str(resume_data)

    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Master resume content is empty.")

    template_style = TemplateStyle(template.value)

    if fmt == ExportFormatQuery.DOCX:
        file_bytes = export_service.generate_docx(
            title=title,
            content_markdown=content,
            full_name=current_user.full_name,
            email=current_user.email,
            template_style=template_style,
            document_type="RESUME",
        )
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = "resume.docx"
    else:
        file_bytes = export_service.generate_pdf(
            title=title,
            content_markdown=content,
            full_name=current_user.full_name,
            email=current_user.email,
            template_style=template_style,
            document_type="RESUME",
        )
        media_type = "application/pdf"
        filename = "resume.pdf"

    return StreamingResponse(
        BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
