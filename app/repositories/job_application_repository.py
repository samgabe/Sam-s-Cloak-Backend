"""Job application repository with specific job operations."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_

from app.models.job_application import JobApplication, ApplicationStatus
from app.repositories.base import BaseRepository
from app.utils.exceptions import DatabaseException


class JobApplicationRepository(BaseRepository[JobApplication]):
    """Repository for JobApplication model operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize job application repository."""
        super().__init__(JobApplication, session)
    
    async def get_by_user_id(
        self, 
        *, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[ApplicationStatus] = None
    ) -> List[JobApplication]:
        """
        Get job applications for a specific user.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of job application instances
        """
        try:
            filters = {"user_id": user_id}
            if status:
                filters["status"] = status
            
            return await self.get_multi(skip=skip, limit=limit, filters=filters)
        except DatabaseException:
            raise
    
    async def get_by_status(
        self, 
        *, 
        status: ApplicationStatus, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[JobApplication]:
        """
        Get job applications by status.
        
        Args:
            status: Application status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of job application instances
        """
        return await self.get_multi(skip=skip, limit=limit, filters={"status": status})
    
    async def search_applications(
        self, 
        *, 
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[JobApplication]:
        """
        Search job applications by text query.
        
        Args:
            user_id: User ID
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching job application instances
        """
        try:
            # Create search conditions
            search_conditions = [
                JobApplication.user_id == user_id,
                or_(
                    JobApplication.job_title.ilike(f"%{query}%"),
                    JobApplication.company_name.ilike(f"%{query}%"),
                    JobApplication.job_description.ilike(f"%{query}%"),
                    JobApplication.location.ilike(f"%{query}%")
                )
            ]
            
            statement = select(JobApplication).where(and_(*search_conditions))
            statement = statement.offset(skip).limit(limit)
            
            result = await self.session.execute(statement)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseException(f"Failed to search job applications: {str(e)}")
    
    async def update_status(
        self, 
        *, 
        application_id: int, 
        status: ApplicationStatus
    ) -> JobApplication:
        """
        Update application status.
        
        Args:
            application_id: Application ID
            status: New status
            
        Returns:
            Updated application instance
        """
        try:
            application = await self.get(id=application_id)
            if not application:
                raise DatabaseException(f"Job application with id {application_id} not found")
            
            return await self.update(db_obj=application, obj_in={"status": status})
        except DatabaseException:
            raise
    
    async def update_ai_analysis(
        self, 
        *, 
        application_id: int, 
        ai_analysis: Dict[str, Any],
        match_score: Optional[float] = None,
        missing_keywords: Optional[List[str]] = None
    ) -> JobApplication:
        """
        Update AI analysis results for an application.
        
        Args:
            application_id: Application ID
            ai_analysis: AI analysis results
            match_score: Optional match score
            missing_keywords: Optional missing keywords list
            
        Returns:
            Updated application instance
        """
        try:
            application = await self.get(id=application_id)
            if not application:
                raise DatabaseException(f"Job application with id {application_id} not found")
            
            update_data = {"ai_analysis": ai_analysis}
            if match_score is not None:
                update_data["match_score"] = match_score
            if missing_keywords is not None:
                update_data["missing_keywords"] = missing_keywords
            
            return await self.update(db_obj=application, obj_in=update_data)
        except DatabaseException:
            raise
    
    async def get_applications_by_match_score(
        self, 
        *, 
        user_id: int,
        min_score: float = 0.0,
        max_score: float = 100.0,
        skip: int = 0,
        limit: int = 100
    ) -> List[JobApplication]:
        """
        Get applications filtered by match score range.
        
        Args:
            user_id: User ID
            min_score: Minimum match score
            max_score: Maximum match score
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of job application instances
        """
        try:
            statement = select(JobApplication).where(
                and_(
                    JobApplication.user_id == user_id,
                    JobApplication.match_score >= min_score,
                    JobApplication.match_score <= max_score
                )
            )
            statement = statement.order_by(JobApplication.match_score.desc())
            statement = statement.offset(skip).limit(limit)
            
            result = await self.session.execute(statement)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseException(f"Failed to get applications by match score: {str(e)}")
    
    async def get_application_statistics(self, *, user_id: int) -> Dict[str, Any]:
        """
        Get application statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with application statistics
        """
        try:
            from sqlalchemy import func
            
            # Count by status
            status_counts = await self.session.execute(
                select(
                    JobApplication.status,
                    func.count(JobApplication.id).label('count')
                ).where(JobApplication.user_id == user_id)
                .group_by(JobApplication.status)
            )
            
            status_stats = {status: count for status, count in status_counts.all()}
            
            # Average match score
            avg_score_result = await self.session.execute(
                select(func.avg(JobApplication.match_score))
                .where(
                    and_(
                        JobApplication.user_id == user_id,
                        JobApplication.match_score.is_not(None)
                    )
                )
            )
            avg_match_score = avg_score_result.scalar() or 0.0
            
            # Total applications
            total_count = await self.count(filters={"user_id": user_id})
            
            return {
                "total_applications": total_count,
                "status_breakdown": status_stats,
                "average_match_score": round(avg_match_score, 2),
                "analyzed_applications": status_stats.get(ApplicationStatus.ANALYZED, 0),
                "applied_applications": status_stats.get(ApplicationStatus.APPLIED, 0)
            }
        except Exception as e:
            raise DatabaseException(f"Failed to get application statistics: {str(e)}")
    
    async def get_recent_applications(
        self, 
        *, 
        user_id: int, 
        days: int = 30,
        limit: int = 10
    ) -> List[JobApplication]:
        """
        Get recent applications for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            List of recent job application instances
        """
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            statement = select(JobApplication).where(
                and_(
                    JobApplication.user_id == user_id,
                    JobApplication.created_at >= cutoff_date
                )
            )
            statement = statement.order_by(JobApplication.created_at.desc())
            statement = statement.limit(limit)
            
            result = await self.session.execute(statement)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseException(f"Failed to get recent applications: {str(e)}")
