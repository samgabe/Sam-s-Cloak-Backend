"""Router imports."""

from app.routers.job_applications import router as job_applications_router
from app.routers.users import router as users_router
from app.routers.documents import router as documents_router

__all__ = [
    "job_applications_router",
    "users_router",
    "documents_router"
]
