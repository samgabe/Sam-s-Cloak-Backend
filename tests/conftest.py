"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from httpx import AsyncClient

from app.main import app
from app.core.database import get_session
from app.core.config import settings


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/samscloak_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator:
    """Create test database and tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = sessionmaker(
        test_db, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator:
    """Create test client with database session override."""
    async def override_get_session():
        yield session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_job_application_data():
    """Sample job application data for testing."""
    return {
        "job_title": "Senior Software Engineer",
        "company_name": "Test Company",
        "job_description": "We are looking for a senior software engineer...",
        "location": "San Francisco, CA",
        "salary_range": "$150k - $200k",
        "remote_type": "hybrid",
        "status": "PENDING"
    }
