"""
Application Configuration & Settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ExamAI"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:yourpassword@localhost:5432/examai_db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./outputs"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"]

    # OCR Settings
    OCR_ENGINE: str = "paddleocr"
    OCR_LANGUAGES: List[str] = ["en", "hi"]
    OCR_CONFIDENCE_THRESHOLD: float = 0.6
    OCR_PARALLEL_WORKERS: int = 4

    # AI Engine (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AI_MODEL: str = "llama3"
    AI_TIMEOUT: int = 120
    AI_MAX_TOKENS: int = 4096

    # Anthropic API
    ANTHROPIC_API_KEY: str = ""
    USE_ANTHROPIC_FALLBACK: bool = False

    # PDF Generation
    PDF_FONT_DIR: str = "./fonts"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields


settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)