"""Model imports."""

from app.models.user import User, UserCreate, UserUpdate, UserRead
from app.models.job_application import (
    JobApplication, 
    JobApplicationCreate, 
    JobApplicationUpdate, 
    JobApplicationRead,
    ApplicationStatus
)
from app.models.tailored_document import (
    TailoredDocument,
    TailoredDocumentCreate,
    TailoredDocumentUpdate,
    TailoredDocumentRead,
    DocumentType
)

__all__ = [
    "User", "UserCreate", "UserUpdate", "UserRead",
    "JobApplication", "JobApplicationCreate", "JobApplicationUpdate", "JobApplicationRead",
    "ApplicationStatus",
    "TailoredDocument", "TailoredDocumentCreate", "TailoredDocumentUpdate", "TailoredDocumentRead",
    "DocumentType"
]
