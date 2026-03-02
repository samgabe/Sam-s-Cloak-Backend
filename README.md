# SamsCloak Backend

Production-ready FastAPI backend for the SamsCloak job application orchestrator.

## Features

- **Async-first architecture** with FastAPI and SQLModel
- **OCR processing** with Tesseract for job posting screenshots
- **AI-powered analysis** using LangChain with OpenAI/Gemini
- **Layered architecture**: Routes → Services → Repositories → Models
- **Type-safe** with Pydantic v2 validation
- **Database migrations** with Alembic
- **Comprehensive error handling** with custom exceptions

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Tesseract OCR

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Setup database:
```bash
# Create PostgreSQL database
createdb samscloak

# Run migrations
alembic upgrade head
```

5. Install Tesseract:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### Running

Development server:
```bash
python -m app.main
# or
uvicorn app.main:app --reload
```

Production server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

```
app/
├── core/           # Configuration and database
├── models/         # SQLModel definitions
├── repositories/   # Data access layer
├── services/       # Business logic layer
├── routers/        # API endpoints
└── utils/          # Utilities and helpers
```

## Key Endpoints

- `POST /api/v1/ingest` - Upload job posting screenshot
- `GET /api/v1/applications/{id}` - Get application with AI analysis
- `POST /api/v1/applications/{id}/analyze` - Perform AI analysis
- `POST /api/v1/applications/{id}/tailor-resume` - Generate tailored resume
- `POST /api/v1/applications/{id}/cover-letter` - Generate cover letter

## Testing

```bash
pytest
```

## Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```
