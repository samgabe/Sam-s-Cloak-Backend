"""Application configuration settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/samscloak"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI Services
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: str = ".png,.jpg,.jpeg,.webp,.pdf"  # Changed from set to str
    
    # OCR
    tesseract_cmd: str = "/usr/bin/tesseract"
    
    @property
    def allowed_extensions_set(self) -> set[str]:
        """Convert allowed_extensions string to set."""
        return set(ext.strip() for ext in self.allowed_extensions.split(","))
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
