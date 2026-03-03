"""PDF extraction service for job postings and resume template extraction."""

from typing import Dict, Any, Optional
import io
from PyPDF2 import PdfReader
import fitz  # PyMuPDF for better PDF handling

from app.utils.exceptions import FileUploadException, ValidationException


class PDFService:
    """Service for extracting text and template information from PDF files."""
    
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
    
    async def extract_template_info(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract template/styling information from a PDF resume.
        
        Args:
            pdf_bytes: PDF file bytes
            
        Returns:
            Dictionary containing template information (fonts, colors, layout)
        """
        try:
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            template_info = {
                "fonts": [],
                "colors": [],
                "layout": {
                    "margins": {},
                    "columns": 1,
                    "sections": []
                },
                "has_images": False,
                "has_tables": False
            }
            
            # Analyze first page for template info
            if len(pdf_document) > 0:
                page = pdf_document[0]
                
                # Extract font information
                fonts_used = set()
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                font_name = span.get("font", "")
                                font_size = span.get("size", 0)
                                color = span.get("color", 0)
                                
                                fonts_used.add((font_name, font_size))
                                
                                # Convert color integer to hex
                                if color:
                                    hex_color = f"#{color:06x}"
                                    if hex_color not in template_info["colors"]:
                                        template_info["colors"].append(hex_color)
                
                template_info["fonts"] = [
                    {"name": font[0], "size": font[1]} 
                    for font in sorted(fonts_used, key=lambda x: x[1], reverse=True)
                ]
                
                # Check for images
                template_info["has_images"] = len(page.get_images()) > 0
                
                # Detect layout structure
                rect = page.rect
                template_info["layout"]["margins"] = {
                    "width": rect.width,
                    "height": rect.height
                }
            
            pdf_document.close()
            return template_info
            
        except Exception as e:
            # Return default template info if extraction fails
            return {
                "fonts": [{"name": "Helvetica", "size": 11}],
                "colors": ["#000000"],
                "layout": {"margins": {}, "columns": 1, "sections": []},
                "has_images": False,
                "has_tables": False
            }
    
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
