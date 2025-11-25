from pathlib import Path
from typing import List, Optional
from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "PolyLab API"
    DEBUG: bool = False
    BACKEND_BASE_URL: str = "https://backend-igra.onrender.com"

    # Security / Sessions
    SECRET_KEY: str = "change-me"
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_TTL_MINUTES: int = 120
    CSRF_COOKIE_NAME: str = "csrf_token"

    # REQUIRED FOR DEPLOYMENT (Render backend + Vercel frontend)
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "none"
    SESSION_COOKIE_DOMAIN: str = "frontend-eight-beige-36.vercel.app"

    # Database
    DATABASE_URL: str = "postgresql://database_z7e0_user:1Njn4LuDETDB09FNTZHEibgZje1g6B0U@dpg-d4i45tp5pdvs739j0nsg-a.oregon-postgres.render.com/database_z7e0"

    # Networking
    FRONTEND_ORIGIN: str = "https://frontend-eight-beige-36.vercel.app"
    CORS_ORIGINS: List[str] = [
        "https://frontend-eight-beige-36.vercel.app",
    ]

    HSTS_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120

    # Files
    UPLOAD_DIR: str = "./uploads"

    # Seed admin (optional)
    ADMIN_EMAIL: Optional[EmailStr] = None
    ADMIN_PASSWORD: Optional[str] = None

    # SMTP / Email for verification
    SMTP_HOST: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None  # YOU MUST ADD IN RENDER ENV
    SMTP_PASSWORD: Optional[str] = None  # YOU MUST ADD IN RENDER ENV
    MAIL_FROM: Optional[EmailStr] = None  # YOU MUST ADD IN RENDER ENV

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        extra="ignore",
    )


settings = Settings()
