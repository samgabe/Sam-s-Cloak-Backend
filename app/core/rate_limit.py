"""Rate limiting middleware for production."""

from typing import Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
import asyncio


class RateLimiter:
    """
    Simple in-memory rate limiter.
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Remove requests older than 1 minute."""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            cutoff_time = current_time - 60
            for ip in list(self.requests.keys()):
                self.requests[ip] = [
                    req_time for req_time in self.requests[ip]
                    if req_time > cutoff_time
                ]
                if not self.requests[ip]:
                    del self.requests[ip]
            self.last_cleanup = current_time
    
    async def __call__(self, request: Request, call_next: Callable):
        """
        Rate limit middleware.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint
            
        Returns:
            Response or rate limit error
        """
        # Get client IP
        client_ip = request.client.host
        
        # Cleanup old requests periodically
        self._cleanup_old_requests()
        
        # Check rate limit
        current_time = time.time()
        cutoff_time = current_time - 60
        
        # Filter requests in last minute
        recent_requests = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff_time
        ]
        
        if len(recent_requests) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": 60
                }
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(recent_requests) - 1
        )
        response.headers["X-RateLimit-Reset"] = str(int(cutoff_time + 60))
        
        return response


# Create rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60)
