"""PDF extraction service for job postings."""

from typing import Dict, Any
import io
from PyPDF2 import PdfReader

from app.utils.exceptions import FileUploadException, ValidationException


class PDFService:
    """Service for extracting text from PDF files."""
    
    def __init__(self):
        """Initialize PDF service."""
        self.max_pages = 10  # Limit to prevent abuse
    
    async def extract_text_from_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from PDF file.
        
        Args:
            pdf_bytes: PDF file bytes
            
        Returns:
            Dictionary containing extracted text and metadata
            
        Raises:
            FileUploadException: If PDF processing fails
            ValidationException: If PDF is invalid or too large
        """
        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            # Validate PDF
            num_pages = len(pdf_reader.pages)
            if num_pages == 0:
                raise ValidationException("PDF file is empty")
            
            if num_pages > self.max_pages:
                raise ValidationException(f"PDF has too many pages (max {self.max_pages})")
            
            # Extract text from all pages
            text_parts = []
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            # Combine all text
            full_text = "\n\n".join(text_parts)
            
            if not full_text.strip():
                raise ValidationException("Could not extract text from PDF")
            
            # Get metadata
            metadata = pdf_reader.metadata or {}
            
            return {
                "raw_text": full_text,
                "num_pages": num_pages,
                "metadata": {
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", "")
                }
            }
            
        except ValidationException:
            raise
        except Exception as e:
            raise FileUploadException(f"Failed to extract text from PDF: {str(e)}")
    
    def is_pdf_file(self, filename: str) -> bool:
        """Check if file is a PDF based on extension."""
        return filename.lower().endswith('.pdf')
    
    async def validate_pdf(self, pdf_bytes: bytes) -> bool:
        """
        Validate PDF file.
        
        Args:
            pdf_bytes: PDF file bytes
            
        Returns:
            True if valid PDF
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            return len(pdf_reader.pages) > 0
        except Exception:
            return False
