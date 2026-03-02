"""Web scraping service for extracting job postings from URLs."""

import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from app.utils.exceptions import ValidationException, AIServiceException


class WebScraperService:
    """Service for scraping job postings from various job sites."""
    
    def __init__(self):
        """Initialize web scraper service."""
        self.timeout = 30.0
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def scrape_job_posting(self, url: str) -> Dict[str, Any]:
        """
        Scrape job posting from URL.
        
        Args:
            url: Job posting URL
            
        Returns:
            Dictionary containing job details
            
        Raises:
            ValidationException: If URL is invalid or unsupported
            AIServiceException: If scraping fails
        """
        # Validate URL
        if not self._is_valid_url(url):
            raise ValidationException("Invalid URL format")
        
        # Determine site type
        domain = self._get_domain(url)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                html_content = response.text
                
                # Route to appropriate scraper based on domain
                if 'linkedin.com' in domain:
                    return await self._scrape_linkedin(html_content, url)
                elif 'indeed.com' in domain:
                    return await self._scrape_indeed(html_content, url)
                elif 'glassdoor.com' in domain:
                    return await self._scrape_glassdoor(html_content, url)
                else:
                    # Generic scraper for other sites
                    return await self._scrape_generic(html_content, url)
                    
        except httpx.HTTPError as e:
            print(f"DEBUG: HTTP error occurred: {str(e)}")
            raise AIServiceException(f"Failed to fetch job posting: {str(e)}")
        except Exception as e:
            print(f"DEBUG: General error occurred: {str(e)}")
            raise AIServiceException(f"Failed to scrape job posting: {str(e)}")
    
    async def _scrape_linkedin(self, html: str, url: str) -> Dict[str, Any]:
        """Scrape LinkedIn job posting."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': ''
        }
        
        # Extract job title
        title_elem = soup.find('h1', class_=re.compile(r'job.*title|top-card.*title'))
        if not title_elem:
            title_elem = soup.find('h1')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Extract company name
        company_elem = soup.find('a', class_=re.compile(r'company.*name|topcard.*org'))
        if not company_elem:
            company_elem = soup.find('span', class_=re.compile(r'company'))
        job_data['company_name'] = company_elem.get_text(strip=True) if company_elem else None
        
        # Extract location
        location_elem = soup.find('span', class_=re.compile(r'location|topcard.*location'))
        job_data['location'] = location_elem.get_text(strip=True) if location_elem else None
        
        # Extract job description
        desc_elem = soup.find('div', class_=re.compile(r'description|show-more'))
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_indeed(self, html: str, url: str) -> Dict[str, Any]:
        """Scrape Indeed job posting."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': ''
        }
        
        # Extract job title
        title_elem = soup.find('h1', class_=re.compile(r'jobsearch.*title'))
        if not title_elem:
            title_elem = soup.find('h1')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Extract company name
        company_elem = soup.find('div', class_=re.compile(r'company'))
        if not company_elem:
            company_elem = soup.find('a', attrs={'data-testid': 'companyName'})
        job_data['company_name'] = company_elem.get_text(strip=True) if company_elem else None
        
        # Extract location
        location_elem = soup.find('div', class_=re.compile(r'location'))
        if not location_elem:
            location_elem = soup.find('div', attrs={'data-testid': 'job-location'})
        job_data['location'] = location_elem.get_text(strip=True) if location_elem else None
        
        # Extract job description
        desc_elem = soup.find('div', id='jobDescriptionText')
        if not desc_elem:
            desc_elem = soup.find('div', class_=re.compile(r'jobsearch.*description'))
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_glassdoor(self, html: str, url: str) -> Dict[str, Any]:
        """Scrape Glassdoor job posting."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': ''
        }
        
        # Extract job title
        title_elem = soup.find('div', class_=re.compile(r'job.*title'))
        if not title_elem:
            title_elem = soup.find('h1')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Extract company name
        company_elem = soup.find('div', class_=re.compile(r'employer'))
        job_data['company_name'] = company_elem.get_text(strip=True) if company_elem else None
        
        # Extract location
        location_elem = soup.find('div', class_=re.compile(r'location'))
        job_data['location'] = location_elem.get_text(strip=True) if location_elem else None
        
        # Extract job description
        desc_elem = soup.find('div', class_=re.compile(r'desc|job.*description'))
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_generic(self, html: str, url: str) -> Dict[str, Any]:
        """Generic scraper for unknown job sites."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': ''
        }
        
        # Try to find job title (usually in h1)
        title_elem = soup.find('h1')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Try to extract main content
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        
        # Get text from body
        body = soup.find('body')
        if body:
            text = body.get_text(separator='\n', strip=True)
            # Clean up excessive whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)
            job_data['job_description'] = text
            job_data['raw_text'] = text
        
        return job_data
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ''
