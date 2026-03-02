"""AI service for job analysis and resume tailoring using LangChain."""

import json
import re
from typing import Dict, Any, List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

from app.core.config import settings
from app.utils.exceptions import AIServiceException


class OptimizationEngine:
    """AI-powered optimization engine for job applications."""
    
    def __init__(self, provider: str = "openai"):
        """
        Initialize AI optimization engine.
        
        Args:
            provider: AI provider to use ("openai" or "gemini")
        """
        self.provider = provider.lower()
        self.llm = self._initialize_llm()
        self.json_parser = JsonOutputParser()
        self.string_parser = StrOutputParser()
    
    def _initialize_llm(self):
        """Initialize the language model based on provider."""
        if self.provider == "openai":
            if not settings.openai_api_key:
                raise AIServiceException("OpenAI API key not configured")
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-4-turbo-preview",
                temperature=0.1
            )
        elif self.provider == "gemini":
            if not settings.gemini_api_key:
                raise AIServiceException("Gemini API key not configured")
            genai.configure(api_key=settings.gemini_api_key)
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                temperature=0.1
            )
        else:
            raise AIServiceException(f"Unsupported AI provider: {self.provider}")
    
    async def analyze_job_fit(
        self, 
        resume_data: Dict[str, Any], 
        job_description: str
    ) -> Dict[str, Any]:
        """
        Perform gap analysis between resume and job description.
        
        Args:
            resume_data: User's resume data
            job_description: Job posting description
            
        Returns:
            Analysis results with match score and recommendations
        """
        try:
            # Extract key information from resume
            resume_text = self._extract_resume_text(resume_data)
            
            # Create analysis prompt
            analysis_prompt = PromptTemplate(
                template="""
                You are an expert career counselor and resume analyst. 
                Analyze the match between a candidate's resume and a job description.
                
                RESUME:
                {resume_text}
                
                JOB DESCRIPTION:
                {job_description}
                
                Provide a detailed analysis in the following JSON format:
                {{
                    "match_score": <number between 0-100>,
                    "strengths": [<list of candidate's strong matches>],
                    "gaps": [<list of missing or weak areas>],
                    "missing_keywords": [<list of important keywords from JD not in resume>],
                    "experience_match": <number between 0-100>,
                    "skills_match": <number between 0-100>,
                    "education_match": <number between 0-100>,
                    "recommendations": [<list of specific improvement suggestions>],
                    "key_requirements": [<list of most important job requirements>]
                }}
                
                Focus on concrete, actionable insights. Be thorough but concise.
                """,
                input_variables=["resume_text", "job_description"]
            )
            
            # Create and run the chain
            chain = analysis_prompt | self.llm | self.json_parser
            
            result = await chain.ainvoke({
                "resume_text": resume_text,
                "job_description": job_description
            })
            
            # Validate and sanitize results
            return self._validate_analysis_result(result)
            
        except Exception as e:
            raise AIServiceException(f"Job fit analysis failed: {str(e)}")
    
    async def tailor_resume(
        self, 
        resume_data: Dict[str, Any], 
        job_description: str,
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        Generate tailored resume based on job description and analysis.
        
        Args:
            resume_data: User's original resume data
            job_description: Target job description
            analysis_result: Results from job fit analysis
            
        Returns:
            Tailored resume in Markdown format
        """
        try:
            resume_text = self._extract_resume_text(resume_data)
            
            # Create tailoring prompt
            tailoring_prompt = PromptTemplate(
                template="""
                You are an expert resume writer. Create a tailored resume that maximizes 
                the candidate's chances for this specific job.
                
                ORIGINAL RESUME:
                {resume_text}
                
                TARGET JOB DESCRIPTION:
                {job_description}
                
                ANALYSIS INSIGHTS:
                {analysis}
                
                Create a tailored resume in Markdown format that:
                1. Highlights relevant experience and skills for this specific role
                2. Incorporates missing keywords naturally
                3. Emphasizes achievements that align with job requirements
                4. Uses strong action verbs and quantifiable results
                5. Maintains professional formatting and readability
                
                Structure the resume with these sections:
                - Contact Information (use placeholders)
                - Professional Summary (tailored to this role)
                - Key Skills (relevant to this job)
                - Work Experience (emphasize relevant achievements)
                - Education
                - Additional Relevant Sections
                
                Use proper Markdown formatting with headers, bullet points, and bold text.
                Do not invent false information. Work only with what's provided in the original resume.
                """,
                input_variables=["resume_text", "job_description", "analysis"]
            )
            
            # Create and run the chain
            chain = tailoring_prompt | self.llm | self.string_parser
            
            tailored_resume = await chain.ainvoke({
                "resume_text": resume_text,
                "job_description": job_description,
                "analysis": json.dumps(analysis_result, indent=2)
            })
            
            return self._format_markdown_resume(tailored_resume)
            
        except Exception as e:
            raise AIServiceException(f"Resume tailoring failed: {str(e)}")
    
    async def generate_cover_letter(
        self, 
        resume_data: Dict[str, Any], 
        job_description: str,
        company_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a personalized cover letter.
        
        Args:
            resume_data: User's resume data
            job_description: Target job description
            company_info: Optional company information
            
        Returns:
            Cover letter in Markdown format
        """
        try:
            resume_text = self._extract_resume_text(resume_data)
            
            # Create cover letter prompt
            cover_letter_prompt = PromptTemplate(
                template="""
                Write a compelling, professional cover letter for this job application.
                
                CANDIDATE BACKGROUND:
                {resume_text}
                
                JOB DESCRIPTION:
                {job_description}
                
                {company_info}
                
                Create a cover letter that:
                1. Is personalized and engaging
                2. Highlights 2-3 key achievements relevant to this role
                3. Shows genuine interest in the company
                4. Demonstrates understanding of the role's requirements
                5. Uses a professional, confident tone
                
                Format as a proper business letter in Markdown with:
                - Date and recipient information
                - Professional greeting
                - 3-4 focused paragraphs
                - Professional closing
                - Signature line
                
                Keep it concise (300-400 words) and impactful.
                """,
                input_variables=["resume_text", "job_description", "company_info"]
            )
            
            company_text = ""
            if company_info:
                company_text = f"COMPANY INFORMATION:\n{json.dumps(company_info, indent=2)}"
            
            # Create and run the chain
            chain = cover_letter_prompt | self.llm | self.string_parser
            
            cover_letter = await chain.ainvoke({
                "resume_text": resume_text,
                "job_description": job_description,
                "company_info": company_text
            })
            
            return self._format_markdown_letter(cover_letter)
            
        except Exception as e:
            raise AIServiceException(f"Cover letter generation failed: {str(e)}")
    
    async def extract_job_metadata(self, job_text: str) -> Dict[str, Any]:
        """
        Extract structured metadata from job posting text.
        
        Args:
            job_text: Raw job posting text
            
        Returns:
            Structured job metadata
        """
        try:
            # Create extraction prompt
            extraction_prompt = PromptTemplate(
                template="""
                Extract structured information from this job posting.
                
                JOB POSTING:
                {job_text}
                
                Return a JSON object with:
                {{
                    "job_title": <string>,
                    "company": <string>,
                    "location": <string>,
                    "remote_type": <"remote", "hybrid", "onsite", or null>,
                    "salary_range": <string or null>,
                    "experience_level": <"entry", "mid", "senior", "lead", or null>,
                    "required_skills": [<list of skills>],
                    "preferred_skills": [<list of skills>],
                    "responsibilities": [<list of key responsibilities>],
                    "qualifications": [<list of qualifications>],
                    "benefits": [<list of benefits>]
                }}
                
                Use null for missing information. Be accurate and only extract what's explicitly mentioned.
                """,
                input_variables=["job_text"]
            )
            
            # Create and run the chain
            chain = extraction_prompt | self.llm | self.json_parser
            
            result = await chain.ainvoke({"job_text": job_text})
            
            return self._validate_extraction_result(result)
            
        except Exception as e:
            raise AIServiceException(f"Job metadata extraction failed: {str(e)}")
    
    def _extract_resume_text(self, resume_data: Dict[str, Any]) -> str:
        """Extract text content from resume data."""
        if isinstance(resume_data, str):
            return resume_data
        elif isinstance(resume_data, dict):
            # Try common keys
            for key in ['text', 'content', 'resume_text', 'body']:
                if key in resume_data and isinstance(resume_data[key], str):
                    return resume_data[key]
            
            # Convert dict to string if no text found
            return json.dumps(resume_data, indent=2)
        else:
            return str(resume_data)
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize analysis results."""
        if not isinstance(result, dict):
            raise AIServiceException("Invalid analysis result format")
        
        # Ensure required fields exist
        defaults = {
            "match_score": 0,
            "strengths": [],
            "gaps": [],
            "missing_keywords": [],
            "experience_match": 0,
            "skills_match": 0,
            "education_match": 0,
            "recommendations": [],
            "key_requirements": []
        }
        
        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
        
        # Validate score ranges
        for score_key in ["match_score", "experience_match", "skills_match", "education_match"]:
            if isinstance(result[score_key], (int, float)):
                result[score_key] = max(0, min(100, result[score_key]))
            else:
                result[score_key] = 0
        
        # Ensure list fields are lists
        for list_key in ["strengths", "gaps", "missing_keywords", "recommendations", "key_requirements"]:
            if not isinstance(result[list_key], list):
                result[list_key] = []
        
        return result
    
    def _validate_extraction_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize extraction results."""
        if not isinstance(result, dict):
            raise AIServiceException("Invalid extraction result format")
        
        # Ensure list fields are lists
        for list_key in ["required_skills", "preferred_skills", "responsibilities", "qualifications", "benefits"]:
            if list_key not in result:
                result[list_key] = []
            elif not isinstance(result[list_key], list):
                result[list_key] = []
        
        return result
    
    def _format_markdown_resume(self, resume_text: str) -> str:
        """Format resume text with proper Markdown structure."""
        # Ensure proper heading levels
        resume_text = re.sub(r'^#', '##', resume_text, flags=re.MULTILINE)
        
        # Format contact info
        resume_text = re.sub(
            r'(?i)contact\s*information?\s*[:\-]*\s*(.+?)(?=\n\n|\n#)',
            r'## Contact Information\n\1',
            resume_text,
            flags=re.DOTALL
        )
        
        return resume_text.strip()
    
    def _format_markdown_letter(self, letter_text: str) -> str:
        """Format cover letter with proper Markdown structure."""
        # Add proper date and greeting formatting
        lines = letter_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if re.match(r'^[A-Za-z]{3,9} \d{1,2}, \d{4}$', line):
                    formatted_lines.append(f"**{line}**")
                elif re.match(r'^Dear .+,$', line):
                    formatted_lines.append(f"\n{line}")
                elif re.match(r'^Sincerely,|Best regards,|Regards,$', line):
                    formatted_lines.append(f"\n{line}")
                else:
                    formatted_lines.append(line)
        
        return '\n'.join(formatted_lines).strip()
