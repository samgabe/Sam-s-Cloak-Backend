"""API routes for job applications."""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.job_application import JobApplication, ApplicationStatus
from app.services.job_application_service import JobApplicationService
from app.utils.exceptions import (
    SamscloakException,
    ValidationException,
    FileUploadException,
    OCRException,
    AIServiceException,
    DatabaseException,
)
from app.core.auth import get_current_user_id
from app.core.config import settings

router = APIRouter()


async def get_job_service(session: AsyncSession = Depends(get_session)) -> JobApplicationService:
    """Get job application service instance."""
    return JobApplicationService(session)


@router.post("/ingest-url", response_model=JobApplication)
async def ingest_job_from_url(
    job_url: str,
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Ingest job posting from URL.
    
    Scrape a job posting from a URL and automatically extract job details,
    then perform AI analysis to match against the user's resume.
    
    - **job_url**: Job posting URL (LinkedIn, Indeed, Glassdoor, etc.)
    - **token**: JWT authentication token
    """
    try:
        application = await job_service.ingest_job_from_url(
            user_id=user_id,
            job_url=job_url
        )
        return application
        
    except (ValidationException, AIServiceException, DatabaseException) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": e.message,
                "details": e.details,
                "error_code": e.error_code
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ingest", response_model=JobApplication)
async def ingest_job_posting(
    file: UploadFile = File(...),
    job_title: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    job_url: Optional[str] = Form(None),
    salary_range: Optional[str] = Form(None),
    remote_type: Optional[str] = Form(None),
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Ingest job posting from screenshot/image or PDF.
    
    Upload a job posting screenshot or PDF and automatically extract job details using OCR/PDF extraction,
    then perform AI analysis to match against the user's resume.
    
    - **file**: Job posting screenshot (PNG, JPG, JPEG, WebP) or PDF
    - **token**: JWT authentication token
    - **job_title**: Optional job title override
    - **company_name**: Optional company name override
    - **location**: Optional location override
    - **job_url**: Optional job posting URL
    - **salary_range**: Optional salary range
    - **remote_type**: Optional remote work type
    """
    try:
        # Validate file
        if not file.content_type:
            raise FileUploadException("File content type is required")
        
        # Check if it's an image or PDF
        is_image = file.content_type.startswith('image/')
        is_pdf = file.content_type == 'application/pdf'
        
        if not is_image and not is_pdf:
            raise FileUploadException("File must be an image or PDF")
        
        if file.size and file.size > settings.max_file_size:
            raise FileUploadException(f"File size exceeds limit of {settings.max_file_size} bytes")
        
        # Read file content
        file_bytes = await file.read()
        
        # Prepare additional data
        additional_data = {}
        if job_title:
            additional_data["job_title"] = job_title
        if company_name:
            additional_data["company_name"] = company_name
        if location:
            additional_data["location"] = location
        if job_url:
            additional_data["job_url"] = job_url
        if salary_range:
            additional_data["salary_range"] = salary_range
        if remote_type:
            additional_data["remote_type"] = remote_type
        
        # Ingest job posting
        application = await job_service.ingest_job_posting(
            user_id=user_id,
            image_bytes=file_bytes,
            filename=file.filename or "upload",
            additional_data=additional_data if additional_data else None
        )
        
        return application
        
    except (ValidationException, FileUploadException, OCRException, AIServiceException, DatabaseException) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": e.message,
                "details": e.details,
                "error_code": e.error_code
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/applications/{application_id}", response_model=JobApplication)
async def get_application(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Get a specific job application with full AI analysis.
    
    Returns the complete job application details including:
    - Job description and metadata
    - AI analysis results
    - Match score and missing keywords
    - Application status and timestamps
    """
    try:
        application = await job_service.get_application_with_analysis(
            application_id=application_id,
            user_id=user_id
        )
        return application
        
    except ValidationException as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/applications", response_model=List[JobApplication])
async def get_user_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[ApplicationStatus] = Query(None),
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Get user's job applications with pagination.
    
    - **skip**: Number of applications to skip (for pagination)
    - **limit**: Maximum number of applications to return (max 1000)
    - **status**: Optional filter by application status
    """
    try:
        applications = await job_service.get_user_applications(
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=status
        )
        return applications
        
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/applications/{application_id}/analyze", response_model=JobApplication)
async def analyze_application(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Perform AI analysis on a job application.
    
    Analyzes the job description against the user's master resume to provide:
    - Match score (0-100)
    - Strengths and gaps
    - Missing keywords
    - Improvement recommendations
    """
    try:
        application = await job_service.analyze_job_application(
            application_id=application_id,
            user_id=user_id
        )
        return application
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/applications/{application_id}/tailor-resume")
async def tailor_resume(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Generate a tailored resume for a specific job application.
    
    Returns a Markdown-formatted resume optimized for the target job,
    incorporating missing keywords and highlighting relevant experience.
    """
    try:
        result = await job_service.tailor_resume(
            application_id=application_id,
            user_id=user_id
        )
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/applications/{application_id}/cover-letter")
async def generate_cover_letter(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Generate a personalized cover letter for a job application.
    
    Returns a Markdown-formatted cover letter tailored to the specific
    job and company, highlighting relevant achievements and skills.
    """
    try:
        result = await job_service.generate_cover_letter(
            application_id=application_id,
            user_id=user_id
        )
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/applications/{application_id}/email")
async def generate_application_email(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service),
):
    """
    Generate a tailored application email (subject and body) for a job.

    This endpoint returns a ready-to-send email payload you can paste into
    Gmail/Outlook:
    - **subject**: Email subject line
    - **body**: Email body text
    """
    try:
        email_payload = await job_service.generate_application_email(
            application_id=application_id,
            user_id=user_id,
        )
        return email_payload
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DatabaseException:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/applications/{application_id}/status", response_model=JobApplication)
async def update_application_status(
    application_id: int,
    status: ApplicationStatus,
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Update the status of a job application.
    
    Valid statuses:
    - PENDING: Newly ingested, not yet analyzed
    - ANALYZED: AI analysis completed
    - APPLIED: Application submitted to employer
    - REJECTED: Application rejected by employer
    - WITHDRAWN: Application withdrawn by user
    """
    try:
        application = await job_service.update_application_status(
            application_id=application_id,
            user_id=user_id,
            status=status
        )
        return application
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/applications/search", response_model=List[JobApplication])
async def search_applications(
    query: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Search user's job applications by text query.
    
    Searches across job titles, company names, descriptions, and locations.
    
    - **query**: Search query string
    - **skip**: Number of results to skip
    - **limit**: Maximum number of results to return
    """
    try:
        applications = await job_service.search_applications(
            user_id=user_id,
            query=query,
            skip=skip,
            limit=limit
        )
        return applications
        
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics")
async def get_application_statistics(
    user_id: int = Depends(get_current_user_id),
    job_service: JobApplicationService = Depends(get_job_service)
):
    """
    Get application statistics for the user.
    
    Returns:
    - Total number of applications
    - Breakdown by status
    - Average match score
    - Recent application trends
    """
    try:
        statistics = await job_service.get_application_statistics(user_id=user_id)
        return statistics
        
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
