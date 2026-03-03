"""Main FastAPI application."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.routers import job_applications_router, users_router, documents_router
from app.utils.exceptions import SamscloakException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="Samscloak API",
    description="High-precision job application orchestrator",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173", "*"],  # Allow all origins for mobile
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(SamscloakException)
async def samscloak_exception_handler(request: Request, exc: SamscloakException):
    """Handle custom Samscloak exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "message": exc.message,
            "details": exc.details,
            "error_code": exc.error_code,
            "type": exc.__class__.__name__
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.detail,
            "type": "HTTPException"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "type": "InternalServerError"
        }
    )


# Include routers
app.include_router(
    users_router,
    prefix=f"{settings.api_prefix}/users",
    tags=["users"]
)

app.include_router(
    job_applications_router,
    prefix=settings.api_prefix,
    tags=["job_applications"]
)

app.include_router(
    documents_router,
    prefix=settings.api_prefix,
    tags=["documents"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Samscloak API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
