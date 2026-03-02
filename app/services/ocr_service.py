"""OCR service with Tesseract wrapper and image preprocessing."""

import io
import re
from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from pytesseract import TesseractError

from app.core.config import settings
from app.utils.exceptions import OCRException


class OCRService:
    """Service for OCR text extraction using Tesseract."""
    
    def __init__(self):
        """Initialize OCR service with Tesseract configuration."""
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        
        # Configure Tesseract parameters for better accuracy
        self.tesseract_config = {
            '--psm': 6,  # Assume a single uniform block of text
            '--oem': 3,  # Use LSTM OCR engine
            '-l': 'eng',  # English language
        }
    
    async def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Resize for better OCR (scale up if too small)
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)
            
            # Apply bilateral filter for noise reduction
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Binarization using adaptive threshold
            image = self._adaptive_threshold(image)
            
            return image
            
        except Exception as e:
            raise OCRException(f"Image preprocessing failed: {str(e)}")
    
    def _adaptive_threshold(self, image: Image.Image) -> Image.Image:
        """Apply adaptive threshold binarization."""
        # Convert to numpy array for processing
        import numpy as np
        
        img_array = np.array(image)
        
        # Apply Otsu's thresholding
        threshold = 0
        max_variance = 0
        
        for t in range(256):
            # Background pixels
            bg_pixels = img_array[img_array <= t]
            # Foreground pixels
            fg_pixels = img_array[img_array > t]
            
            if len(bg_pixels) == 0 or len(fg_pixels) == 0:
                continue
            
            # Calculate weights
            w0 = len(bg_pixels) / img_array.size
            w1 = len(fg_pixels) / img_array.size
            
            # Calculate means
            mean0 = np.mean(bg_pixels) if len(bg_pixels) > 0 else 0
            mean1 = np.mean(fg_pixels) if len(fg_pixels) > 0 else 0
            
            # Calculate between-class variance
            variance = w0 * w1 * (mean0 - mean1) ** 2
            
            if variance > max_variance:
                max_variance = variance
                threshold = t
        
        # Apply threshold
        binary_array = (img_array > threshold).astype(np.uint8) * 255
        return Image.fromarray(binary_array)
    
    async def extract_text(self, image_bytes: bytes) -> str:
        """
        Extract text from image bytes using OCR.
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            Extracted text string
            
        Raises:
            OCRException: If OCR processing fails
        """
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess image
            processed_image = await self.preprocess_image(image)
            
            # Extract text using Tesseract
            config_str = ' '.join(f'{k} {v}' for k, v in self.tesseract_config.items())
            
            text = pytesseract.image_to_string(
                processed_image,
                config=config_str
            )
            
            # Clean and post-process text
            cleaned_text = self._clean_text(text)
            
            return cleaned_text
            
        except TesseractError as e:
            raise OCRException(f"Tesseract OCR error: {str(e)}")
        except Exception as e:
            raise OCRException(f"OCR processing failed: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        corrections = {
            r'\b0\b': 'O',  # Zero to O
            r'\b1\b': 'I',  # One to I in certain contexts
            r'\b5\b': 'S',  # Five to S in certain contexts
            r'\b8\b': 'B',  # Eight to B in certain contexts
            r'\|': 'I',     # Pipe to I
            r'\[\]': 'O',   # Empty brackets to O
            r'\(\)': 'O',   # Empty parentheses to O
        }
        
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text)
        
        # Remove non-printable characters except newlines
        text = re.sub(r'[^\x20-\x7E\n]', '', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s*([.,;:!])', r'\1', text)
        text = re.sub(r'([.,;:!])\s*', r'\1 ', text)
        
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    async def extract_structured_data(self, image_bytes: bytes) -> dict:
        """
        Extract structured data from image using OCR with pattern matching.
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            Dictionary containing structured job posting data
        """
        text = await self.extract_text(image_bytes)
        
        # Extract job title (usually at the beginning, in larger font)
        job_title_patterns = [
            r'^(.+?)(?:\n|$)',  # First line
            r'(?:Job Title|Position|Role)[:\s]+(.+?)(?:\n|$)',
            r'(?:We are hiring|Looking for|Seeking)[:\s]+(.+?)(?:\n|$)',
        ]
        
        job_title = self._extract_pattern(text, job_title_patterns)
        
        # Extract company name
        company_patterns = [
            r'(?:Company|Organization)[:\s]+(.+?)(?:\n|$)',
            r'^(.+?)(?:\n.+?\n)',  # Usually second line
            r'(?:at|@)\s+([A-Za-z\s]+?)(?:\n|$)',
        ]
        
        company = self._extract_pattern(text, company_patterns)
        
        # Extract location
        location_patterns = [
            r'(?:Location|City|State)[:\s]+(.+?)(?:\n|$)',
            r'([A-Za-z\s]+,\s*[A-Z]{2})',
            r'([A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})',
        ]
        
        location = self._extract_pattern(text, location_patterns)
        
        # Extract salary/range
        salary_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[-–]\s*\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:Salary|Pay|Compensation)[:\s]+\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}k?\s*[-–]\s*\d{1,3}k?)',
        ]
        
        salary = self._extract_pattern(text, salary_patterns)
        
        return {
            "raw_text": text,
            "extracted_data": {
                "job_title": job_title,
                "company": company,
                "location": location,
                "salary_range": salary,
            }
        }
    
    def _extract_pattern(self, text: str, patterns: list) -> Optional[str]:
        """Extract text using multiple regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result = match.group(1) if match.groups() else match.group(0)
                return result.strip() if result else None
        return None
    
    async def validate_ocr_quality(self, image_bytes: bytes) -> Tuple[bool, float]:
        """
        Validate OCR quality by checking text confidence.
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            Tuple of (is_valid_quality, confidence_score)
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            processed_image = await self.preprocess_image(image)
            
            # Get OCR data with confidence scores
            data = pytesseract.image_to_data(
                processed_image,
                config=' '.join(f'{k} {v}' for k, v in self.tesseract_config.items()),
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Consider valid if confidence > 60%
            is_valid = avg_confidence > 60
            
            return is_valid, avg_confidence
            
        except Exception:
            return False, 0.0
