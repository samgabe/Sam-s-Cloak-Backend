"""Enhanced web scraping service for extracting job postings from diverse URLs."""

import re
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
import httpx
from bs4 import BeautifulSoup
from datetime import datetime

from app.utils.exceptions import ValidationException, AIServiceException


class WebScraperService:
    """Advanced service for scraping job postings from various job sites with rich data extraction."""
    
    def __init__(self):
        """Initialize web scraper service."""
        self.timeout = 30.0
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Patterns for extracting structured data
        self.salary_patterns = [
            r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?(?:\s*(?:per|/)\s*(?:year|yr|hour|hr|month|mo))?',
            r'[\d,]+k?\s*-\s*[\d,]+k?\s*(?:USD|EUR|GBP)?',
            r'(?:salary|compensation):\s*\$?[\d,]+(?:\s*-\s*\$?[\d,]+)?'
        ]
        
        self.remote_patterns = [
            r'\b(remote|hybrid|on-?site|in-?office|work from home|wfh)\b',
            r'\b(fully remote|100% remote|remote-first)\b'
        ]
        
        self.experience_patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            r'(?:experience|exp):\s*(\d+)\+?\s*(?:years?|yrs?)',
            r'(\d+)-(\d+)\s*(?:years?|yrs?)'
        ]
    
    async def scrape_job_posting(self, url: str) -> Dict[str, Any]:
        """
        Scrape job posting from URL with rich data extraction.
        
        Args:
            url: Job posting URL
            
        Returns:
            Dictionary containing comprehensive job details
            
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
            async with httpx.AsyncClient(
                timeout=self.timeout, 
                headers=self.headers, 
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                html_content = response.text
                
                # Try to extract JSON-LD structured data first
                structured_data = self._extract_json_ld(html_content)
                
                # Route to appropriate scraper based on domain
                if 'linkedin.com' in domain:
                    job_data = await self._scrape_linkedin(html_content, url)
                elif 'indeed.com' in domain:
                    job_data = await self._scrape_indeed(html_content, url)
                elif 'glassdoor.com' in domain:
                    job_data = await self._scrape_glassdoor(html_content, url)
                elif 'greenhouse.io' in domain:
                    job_data = await self._scrape_greenhouse(html_content, url)
                elif 'lever.co' in domain:
                    job_data = await self._scrape_lever(html_content, url)
                elif 'workday.com' in domain or 'myworkdayjobs.com' in domain:
                    job_data = await self._scrape_workday(html_content, url)
                elif 'jobs.apple.com' in domain or 'careers.google.com' in domain or 'amazon.jobs' in domain:
                    job_data = await self._scrape_tech_company(html_content, url, domain)
                else:
                    # Generic scraper for other sites
                    job_data = await self._scrape_generic(html_content, url)
                
                # Merge with structured data if available
                if structured_data:
                    job_data = self._merge_job_data(job_data, structured_data)
                
                # Extract additional metadata
                job_data = self._enrich_job_data(job_data)
                
                return job_data
                    
        except httpx.HTTPError as e:
            print(f"HTTP error occurred: {str(e)}")
            raise AIServiceException(f"Failed to fetch job posting: {str(e)}")
        except Exception as e:
            print(f"Scraping error occurred: {str(e)}")
            raise AIServiceException(f"Failed to scrape job posting: {str(e)}")
    
    def _extract_json_ld(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract JSON-LD structured data from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                        return data
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                return item
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"JSON-LD extraction failed: {e}")
        
        return None

    async def _scrape_linkedin(self, html: str, url: str) -> Dict[str, Any]:
        """Enhanced LinkedIn scraper."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': 'LinkedIn'
        }
        
        # Extract job title
        title_selectors = [
            ('h1', {'class': re.compile(r'top-card-layout__title|job-details-jobs-unified-top-card__job-title')}),
            ('h1', {'class': re.compile(r'topcard__title')}),
            ('h1', {})
        ]
        job_data['job_title'] = self._find_text(soup, title_selectors)
        
        # Extract company name
        company_selectors = [
            ('a', {'class': re.compile(r'topcard__org-name-link|job-details-jobs-unified-top-card__company-name')}),
            ('span', {'class': re.compile(r'topcard__flavor')}),
            ('a', {'class': re.compile(r'company')})
        ]
        job_data['company_name'] = self._find_text(soup, company_selectors)
        
        # Extract location
        location_selectors = [
            ('span', {'class': re.compile(r'topcard__flavor--bullet|job-details-jobs-unified-top-card__bullet')}),
            ('span', {'class': re.compile(r'location')})
        ]
        job_data['location'] = self._find_text(soup, location_selectors)
        
        # Extract job description
        desc_selectors = [
            ('div', {'class': re.compile(r'show-more-less-html__markup|description__text')}),
            ('div', {'class': re.compile(r'description')})
        ]
        desc_elem = self._find_element(soup, desc_selectors)
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        # Extract job criteria (seniority, employment type, etc.)
        criteria = soup.find_all('li', class_=re.compile(r'job-criteria'))
        for item in criteria:
            label = item.find('h3')
            value = item.find('span')
            if label and value:
                key = label.get_text(strip=True).lower().replace(' ', '_')
                job_data[key] = value.get_text(strip=True)
        
        return job_data
    
    async def _scrape_indeed(self, html: str, url: str) -> Dict[str, Any]:
        """Enhanced Indeed scraper."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': 'Indeed'
        }
        
        # Extract job title
        title_selectors = [
            ('h1', {'class': re.compile(r'jobsearch-JobInfoHeader-title')}),
            ('h1', {'data-testid': 'jobsearch-JobInfoHeader-title'}),
            ('h1', {})
        ]
        job_data['job_title'] = self._find_text(soup, title_selectors)
        
        # Extract company name
        company_selectors = [
            ('div', {'data-testid': 'inlineHeader-companyName'}),
            ('a', {'data-testid': 'companyName'}),
            ('div', {'class': re.compile(r'company')})
        ]
        job_data['company_name'] = self._find_text(soup, company_selectors)
        
        # Extract location
        location_selectors = [
            ('div', {'data-testid': 'job-location'}),
            ('div', {'class': re.compile(r'location')})
        ]
        job_data['location'] = self._find_text(soup, location_selectors)
        
        # Extract salary
        salary_selectors = [
            ('div', {'id': 'salaryInfoAndJobType'}),
            ('span', {'class': re.compile(r'salary')})
        ]
        job_data['salary_range'] = self._find_text(soup, salary_selectors)
        
        # Extract job description
        desc_selectors = [
            ('div', {'id': 'jobDescriptionText'}),
            ('div', {'class': re.compile(r'jobsearch-jobDescriptionText')})
        ]
        desc_elem = self._find_element(soup, desc_selectors)
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_glassdoor(self, html: str, url: str) -> Dict[str, Any]:
        """Enhanced Glassdoor scraper."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': 'Glassdoor'
        }
        
        # Extract job title
        title_selectors = [
            ('div', {'data-test': 'job-title'}),
            ('h1', {'class': re.compile(r'job.*title')}),
            ('h1', {})
        ]
        job_data['job_title'] = self._find_text(soup, title_selectors)
        
        # Extract company name
        company_selectors = [
            ('div', {'data-test': 'employer-name'}),
            ('div', {'class': re.compile(r'employer')})
        ]
        job_data['company_name'] = self._find_text(soup, company_selectors)
        
        # Extract location
        location_selectors = [
            ('div', {'data-test': 'location'}),
            ('div', {'class': re.compile(r'location')})
        ]
        job_data['location'] = self._find_text(soup, location_selectors)
        
        # Extract job description
        desc_selectors = [
            ('div', {'class': re.compile(r'jobDescriptionContent')}),
            ('div', {'class': re.compile(r'desc')})
        ]
        desc_elem = self._find_element(soup, desc_selectors)
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_greenhouse(self, html: str, url: str) -> Dict[str, Any]:
        """Scrape Greenhouse ATS job postings."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': 'Greenhouse'
        }
        
        # Greenhouse has a clean structure
        title_elem = soup.find('h1', class_='app-title')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        location_elem = soup.find('div', class_='location')
        job_data['location'] = location_elem.get_text(strip=True) if location_elem else None
        
        # Description is usually in #content div
        desc_elem = soup.find('div', id='content')
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_lever(self, html: str, url: str) -> Dict[str, Any]:
        """Scrape Lever ATS job postings."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': 'Lever'
        }
        
        title_elem = soup.find('h2', class_='posting-headline')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        location_elem = soup.find('div', class_='posting-categories')
        if location_elem:
            location_text = location_elem.find('div', class_='location')
            job_data['location'] = location_text.get_text(strip=True) if location_text else None
        
        desc_elem = soup.find('div', class_='posting-description')
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_workday(self, html: str, url: str) -> Dict[str, Any]:
        """Scrape Workday job postings."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': 'Workday'
        }
        
        title_elem = soup.find('h2', attrs={'data-automation-id': 'jobPostingHeader'})
        if not title_elem:
            title_elem = soup.find('h1')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Workday uses data-automation-id attributes
        location_elem = soup.find('div', attrs={'data-automation-id': 'locations'})
        job_data['location'] = location_elem.get_text(strip=True) if location_elem else None
        
        desc_elem = soup.find('div', attrs={'data-automation-id': 'jobPostingDescription'})
        if desc_elem:
            job_data['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_tech_company(self, html: str, url: str, domain: str) -> Dict[str, Any]:
        """Scrape major tech company career pages (Apple, Google, Amazon, etc.)."""
        soup = BeautifulSoup(html, 'html.parser')
        
        company_name = None
        if 'apple.com' in domain:
            company_name = 'Apple'
        elif 'google.com' in domain:
            company_name = 'Google'
        elif 'amazon' in domain:
            company_name = 'Amazon'
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': company_name or 'Tech Company',
            'company_name': company_name
        }
        
        # Try common selectors
        title_elem = soup.find('h1')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Look for main content
        main_content = soup.find('main') or soup.find('div', {'role': 'main'})
        if main_content:
            job_data['job_description'] = main_content.get_text(separator='\n', strip=True)
            job_data['raw_text'] = job_data['job_description']
        
        return job_data
    
    async def _scrape_generic(self, html: str, url: str) -> Dict[str, Any]:
        """Enhanced generic scraper with better content extraction."""
        soup = BeautifulSoup(html, 'html.parser')
        
        job_data = {
            'job_url': url,
            'raw_text': '',
            'source': 'Generic'
        }
        
        # Try to find job title
        title_elem = soup.find('h1')
        job_data['job_title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            element.decompose()
        
        # Try to find main content area
        main_content = (
            soup.find('main') or 
            soup.find('article') or
            soup.find('div', {'role': 'main'}) or
            soup.find('div', class_=re.compile(r'content|job|description|posting', re.I)) or
            soup.find('body')
        )
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
            # Clean up excessive whitespace
            text = re.sub(r'\n\s*\n+', '\n\n', text)
            text = re.sub(r' +', ' ', text)
            job_data['job_description'] = text
            job_data['raw_text'] = text
        
        return job_data
    
    def _merge_job_data(self, scraped_data: Dict[str, Any], structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge scraped data with JSON-LD structured data."""
        if not structured_data:
            return scraped_data
        
        # Map JSON-LD fields to our schema
        if 'title' in structured_data and not scraped_data.get('job_title'):
            scraped_data['job_title'] = structured_data['title']
        
        if 'hiringOrganization' in structured_data and not scraped_data.get('company_name'):
            org = structured_data['hiringOrganization']
            if isinstance(org, dict):
                scraped_data['company_name'] = org.get('name')
        
        if 'jobLocation' in structured_data and not scraped_data.get('location'):
            location = structured_data['jobLocation']
            if isinstance(location, dict):
                address = location.get('address', {})
                if isinstance(address, dict):
                    scraped_data['location'] = address.get('addressLocality') or address.get('addressRegion')
        
        if 'baseSalary' in structured_data and not scraped_data.get('salary_range'):
            salary = structured_data['baseSalary']
            if isinstance(salary, dict):
                value = salary.get('value', {})
                if isinstance(value, dict):
                    min_val = value.get('minValue')
                    max_val = value.get('maxValue')
                    if min_val and max_val:
                        scraped_data['salary_range'] = f"${min_val} - ${max_val}"
        
        if 'description' in structured_data and not scraped_data.get('job_description'):
            scraped_data['job_description'] = structured_data['description']
            scraped_data['raw_text'] = structured_data['description']
        
        return scraped_data
    
    def _enrich_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract additional metadata from job description."""
        description = job_data.get('job_description', '') or job_data.get('raw_text', '')
        
        if not description:
            return job_data
        
        # Extract salary if not already present
        if not job_data.get('salary_range'):
            for pattern in self.salary_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    job_data['salary_range'] = match.group(0)
                    break
        
        # Extract remote type
        if not job_data.get('remote_type'):
            for pattern in self.remote_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    remote_text = match.group(0).lower()
                    if 'remote' in remote_text:
                        job_data['remote_type'] = 'Remote'
                    elif 'hybrid' in remote_text:
                        job_data['remote_type'] = 'Hybrid'
                    else:
                        job_data['remote_type'] = 'On-site'
                    break
        
        # Extract experience requirements
        for pattern in self.experience_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                years = match.group(1)
                job_data['experience_required'] = f"{years}+ years"
                break
        
        # Add timestamp
        job_data['scraped_at'] = datetime.utcnow().isoformat()
        
        return job_data
    
    def _find_element(self, soup: BeautifulSoup, selectors: List[tuple]) -> Optional[Any]:
        """Find element using multiple selectors."""
        for tag, attrs in selectors:
            elem = soup.find(tag, attrs)
            if elem:
                return elem
        return None
    
    def _find_text(self, soup: BeautifulSoup, selectors: List[tuple]) -> Optional[str]:
        """Find text using multiple selectors."""
        elem = self._find_element(soup, selectors)
        return elem.get_text(strip=True) if elem else None
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ''
