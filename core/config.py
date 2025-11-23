from pathlib import Path
from typing import List, Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "PolyLab API"
    DEBUG: bool = True
    BACKEND_BASE_URL: str = "http://127.0.0.1:8000"

    # Security / Sessions
    SECRET_KEY: str = "change-me"
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_TTL_MINUTES: int = 120
    CSRF_COOKIE_NAME: str = "csrf_token"

    # Database
    DATABASE_URL: str = "sqlite:///./polylab.db"

    # Networking
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://127.0.0.1"]
    HSTS_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 120

    # Files
    UPLOAD_DIR: str = "./uploads"

    # Seed admin (optional)
    ADMIN_EMAIL: Optional[EmailStr] = None
    ADMIN_PASSWORD: Optional[str] = None

    # SMTP / email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[EmailStr] = None

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        extra="ignore",
    )


settings = Settings()
