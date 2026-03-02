"""Job application service with business logic."""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_application import JobApplication, JobApplicationCreate, ApplicationStatus
from app.models.user import User
from app.repositories.job_application_repository import JobApplicationRepository
from app.repositories.user_repository import UserRepository
from app.services.ocr_service import OCRService
from app.services.ai_service import OptimizationEngine
from app.services.web_scraper_service import WebScraperService
from app.services.pdf_service import PDFService
from app.utils.exceptions import (
    DatabaseException, 
    OCRException, 
    AIServiceException,
    ValidationException,
    FileUploadException
)
from app.utils.security import sanitize_string, validate_file_extension
from app.core.config import settings


class JobApplicationService:
    """Service for job application business logic."""
    
    def __init__(self, session: AsyncSession):
        """Initialize job application service."""
        self.session = session
        self.job_repo = JobApplicationRepository(session)
        self.user_repo = UserRepository(session)
        self.ocr_service = OCRService()
        self.ai_engine = OptimizationEngine()
        self.web_scraper = WebScraperService()
        self.pdf_service = PDFService()
    
    async def ingest_job_posting(
        self, 
        *, 
        user_id: int,
        image_bytes: bytes,
        filename: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> JobApplication:
        """
        Ingest job posting from screenshot/image or PDF.
        
        Args:
            user_id: User ID
            image_bytes: Image or PDF data
            filename: Original filename
            additional_data: Additional job metadata
            
        Returns:
            Created job application with OCR/PDF extraction and AI analysis
            
        Raises:
            ValidationException: If input validation fails
            FileUploadException: If file processing fails
            OCRException: If OCR processing fails
            AIServiceException: If AI analysis fails
            DatabaseException: If database operations fail
        """
        try:
            # Validate user exists
            user = await self.user_repo.get(id=user_id)
            if not user:
                raise ValidationException(f"User with id {user_id} not found")
            
            # Check if file is PDF
            is_pdf = self.pdf_service.is_pdf_file(filename)
            
            if is_pdf:
                # Extract text from PDF
                pdf_result = await self.pdf_service.extract_text_from_pdf(image_bytes)
                raw_text = pdf_result["raw_text"]
                extracted_data = {}
            else:
                # Validate image file
                if not validate_file_extension(filename, settings.allowed_extensions_set):
                    raise FileUploadException(f"Invalid file type: {filename}")
                
                # Extract text using OCR
                ocr_result = await self.ocr_service.extract_structured_data(image_bytes)
                raw_text = ocr_result["raw_text"]
                extracted_data = ocr_result["extracted_data"]
                
                # Validate OCR quality
                is_valid_quality, confidence = await self.ocr_service.validate_ocr_quality(image_bytes)
                if not is_valid_quality:
                    raise OCRException(f"Low OCR quality: {confidence:.1f}% confidence")
            
            # Extract job metadata using AI
            job_metadata = await self.ai_engine.extract_job_metadata(raw_text)
            
            # Merge extracted data with additional data
            job_data = {
                "job_title": extracted_data.get("job_title") or job_metadata.get("job_title", "Unknown Position"),
                "company_name": extracted_data.get("company") or job_metadata.get("company", "Unknown Company"),
                "job_description": raw_text,
                "location": extracted_data.get("location") or job_metadata.get("location"),
                "salary_range": extracted_data.get("salary_range") or job_metadata.get("salary_range"),
                "remote_type": job_metadata.get("remote_type"),
                "raw_text": raw_text,
                "user_id": user_id,
                "status": ApplicationStatus.PENDING
            }
            
            # Merge with additional data if provided
            if additional_data:
                job_data.update(additional_data)
            
            # Sanitize string fields
            for key, value in job_data.items():
                if isinstance(value, str):
                    job_data[key] = sanitize_string(value, max_length=1000 if key == "job_description" else 255)
            
            # Create job application
            job_application = await self.job_repo.create(obj_in=job_data)
            
            # Perform AI analysis if user has master resume
            if user.master_resume:
                await self._perform_ai_analysis(job_application, user.master_resume)
            
            return job_application
            
        except (ValidationException, FileUploadException, OCRException, AIServiceException, DatabaseException):
            raise
        except Exception as e:
            raise DatabaseException(f"Job posting ingestion failed: {str(e)}")
    
    async def ingest_job_from_url(
        self, 
        *, 
        user_id: int,
        job_url: str
    ) -> JobApplication:
        """
        Ingest job posting from URL.
        
        Args:
            user_id: User ID
            job_url: Job posting URL
            
        Returns:
            Created job application with AI analysis
            
        Raises:
            ValidationException: If input validation fails
            AIServiceException: If scraping or AI analysis fails
            DatabaseException: If database operations fail
        """
        try:
            # Validate user exists
            user = await self.user_repo.get(id=user_id)
            if not user:
                raise ValidationException(f"User with id {user_id} not found")
            
            # Scrape job posting from URL
            scraped_data = await self.web_scraper.scrape_job_posting(job_url)
            
            # Extract job metadata using AI if description is available
            raw_text = scraped_data.get('job_description') or scraped_data.get('raw_text', '')
            
            if not raw_text:
                raise ValidationException("Could not extract job description from URL")
            
            # Extract additional metadata using AI
            job_metadata = await self.ai_engine.extract_job_metadata(raw_text)
            
            # Prepare job data
            job_data = {
                "job_title": scraped_data.get("job_title") or job_metadata.get("job_title", "Unknown Position"),
                "company_name": scraped_data.get("company_name") or job_metadata.get("company", "Unknown Company"),
                "job_description": raw_text,
                "location": scraped_data.get("location") or job_metadata.get("location"),
                "salary_range": scraped_data.get("salary_range") or job_metadata.get("salary_range"),
                "remote_type": scraped_data.get("remote_type") or job_metadata.get("remote_type"),
                "job_url": job_url,
                "raw_text": raw_text,
                "user_id": user_id,
                "status": ApplicationStatus.PENDING
            }
            
            # Sanitize string fields
            for key, value in job_data.items():
                if isinstance(value, str):
                    job_data[key] = sanitize_string(value, max_length=1000 if key == "job_description" else 255)
            
            # Create job application
            job_application = await self.job_repo.create(obj_in=job_data)
            
            # Perform AI analysis if user has master resume
            if user.master_resume:
                await self._perform_ai_analysis(job_application, user.master_resume)
            
            return job_application
            
        except (ValidationException, AIServiceException, DatabaseException):
            raise
        except Exception as e:
            raise DatabaseException(f"Job URL ingestion failed: {str(e)}")
    
    async def analyze_job_application(
        self, 
        *, 
        application_id: int,
        user_id: int
    ) -> JobApplication:
        """
        Perform AI analysis on a job application.
        
        Args:
            application_id: Job application ID
            user_id: User ID (for authorization)
            
        Returns:
            Updated job application with AI analysis
        """
        try:
            # Get application and verify ownership
            application = await self.job_repo.get(id=application_id)
            if not application:
                raise ValidationException(f"Job application with id {application_id} not found")
            
            if application.user_id != user_id:
                raise ValidationException("Unauthorized access to job application")
            
            # Get user's master resume
            user = await self.user_repo.get(id=user_id)
            if not user or not user.master_resume:
                raise ValidationException("User master resume not found")
            
            # Perform AI analysis
            await self._perform_ai_analysis(application, user.master_resume)
            
            # Update status to ANALYZED
            application = await self.job_repo.update_status(
                application_id=application_id,
                status=ApplicationStatus.ANALYZED
            )
            
            return application
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            raise DatabaseException(f"Job application analysis failed: {str(e)}")
    
    async def tailor_resume(
        self, 
        *, 
        application_id: int,
        user_id: int
    ) -> str:
        """
        Generate tailored resume for a job application.
        
        Args:
            application_id: Job application ID
            user_id: User ID (for authorization)
            
        Returns:
            Tailored resume in Markdown format
        """
        try:
            # Get application and verify ownership
            application = await self.job_repo.get(id=application_id)
            if not application:
                raise ValidationException(f"Job application with id {application_id} not found")
            
            if application.user_id != user_id:
                raise ValidationException("Unauthorized access to job application")
            
            # Get user's master resume
            user = await self.user_repo.get(id=user_id)
            if not user or not user.master_resume:
                raise ValidationException("User master resume not found")
            
            # Check if AI analysis exists
            if not application.ai_analysis:
                await self.analyze_job_application(application_id=application_id, user_id=user_id)
                application = await self.job_repo.get(id=application_id)
            
            # Generate tailored resume
            tailored_resume = await self.ai_engine.tailor_resume(
                resume_data=user.master_resume,
                job_description=application.job_description,
                analysis_result=application.ai_analysis
            )
            
            return tailored_resume
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            raise DatabaseException(f"Resume tailoring failed: {str(e)}")
    
    async def generate_cover_letter(
        self, 
        *, 
        application_id: int,
        user_id: int
    ) -> str:
        """
        Generate cover letter for a job application.
        
        Args:
            application_id: Job application ID
            user_id: User ID (for authorization)
            
        Returns:
            Cover letter in Markdown format
        """
        try:
            # Get application and verify ownership
            application = await self.job_repo.get(id=application_id)
            if not application:
                raise ValidationException(f"Job application with id {application_id} not found")
            
            if application.user_id != user_id:
                raise ValidationException("Unauthorized access to job application")
            
            # Get user's master resume
            user = await self.user_repo.get(id=user_id)
            if not user:
                raise ValidationException(f"User with id {user_id} not found")
            
            if not user.master_resume:
                raise ValidationException("Please upload your master resume first before generating tailored resumes")
            
            # Prepare company info
            company_info = {
                "name": application.company_name,
                "location": application.location,
                "job_title": application.job_title
            }
            
            # Generate cover letter
            cover_letter = await self.ai_engine.generate_cover_letter(
                resume_data=user.master_resume,
                job_description=application.job_description,
                company_info=company_info
            )
            
            return cover_letter
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            raise DatabaseException(f"Cover letter generation failed: {str(e)}")
    
    async def get_application_with_analysis(
        self, 
        *, 
        application_id: int,
        user_id: int
    ) -> JobApplication:
        """
        Get job application with full analysis.
        
        Args:
            application_id: Job application ID
            user_id: User ID (for authorization)
            
        Returns:
            Job application with AI analysis
        """
        try:
            application = await self.job_repo.get(id=application_id)
            if not application:
                raise ValidationException(f"Job application with id {application_id} not found")
            
            if application.user_id != user_id:
                raise ValidationException("Unauthorized access to job application")
            
            return application
            
        except ValidationException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to get job application: {str(e)}")
    
    async def get_user_applications(
        self, 
        *, 
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None
    ) -> List[JobApplication]:
        """
        Get user's job applications with pagination.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of job applications
        """
        try:
            return await self.job_repo.get_by_user_id(
                user_id=user_id,
                skip=skip,
                limit=limit,
                status=status
            )
        except Exception as e:
            raise DatabaseException(f"Failed to get user applications: {str(e)}")
    
    async def update_application_status(
        self, 
        *, 
        application_id: int,
        user_id: int,
        status: ApplicationStatus
    ) -> JobApplication:
        """
        Update job application status.
        
        Args:
            application_id: Job application ID
            user_id: User ID (for authorization)
            status: New status
            
        Returns:
            Updated job application
        """
        try:
            # Verify ownership
            application = await self.job_repo.get(id=application_id)
            if not application:
                raise ValidationException(f"Job application with id {application_id} not found")
            
            if application.user_id != user_id:
                raise ValidationException("Unauthorized access to job application")
            
            return await self.job_repo.update_status(
                application_id=application_id,
                status=status
            )
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to update application status: {str(e)}")
    
    async def get_application_statistics(self, *, user_id: int) -> Dict[str, Any]:
        """
        Get application statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Application statistics
        """
        try:
            return await self.job_repo.get_application_statistics(user_id=user_id)
        except Exception as e:
            raise DatabaseException(f"Failed to get application statistics: {str(e)}")
    
    async def search_applications(
        self, 
        *, 
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[JobApplication]:
        """
        Search user's job applications.
        
        Args:
            user_id: User ID
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching job applications
        """
        try:
            return await self.job_repo.search_applications(
                user_id=user_id,
                query=query,
                skip=skip,
                limit=limit
            )
        except Exception as e:
            raise DatabaseException(f"Failed to search applications: {str(e)}")
    
    async def _perform_ai_analysis(
        self, 
        application: JobApplication, 
        master_resume: Dict[str, Any]
    ) -> None:
        """
        Perform AI analysis on job application.
        
        Args:
            application: Job application instance
            master_resume: User's master resume data
        """
        try:
            # Analyze job fit
            analysis_result = await self.ai_engine.analyze_job_fit(
                resume_data=master_resume,
                job_description=application.job_description
            )
            
            # Update application with AI analysis
            await self.job_repo.update_ai_analysis(
                application_id=application.id,
                ai_analysis=analysis_result,
                match_score=analysis_result.get("match_score"),
                missing_keywords=analysis_result.get("missing_keywords", [])
            )
            
        except AIServiceException:
            raise
        except Exception as e:
            raise AIServiceException(f"AI analysis failed: {str(e)}")
