from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    # Allow running `uvicorn main:app` from inside Backend/
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    __package__ = "Backend"

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.csrf import csrf_protect
from core.ratelimit import rate_limit
from core.security import hash_password, password_policy_ok
from database import Base, SessionLocal, engine
from middleware.security_headers import SecurityHeadersMiddleware
from routers import (
    admin,
    assignment,
    auth,
    classrooms,
    materials,
    instructor_requests,
    me,
    mfa,
    quiz,
    submission,
)
from models import User, UserRole

Base.metadata.create_all(bind=engine)


def ensure_seed_admin() -> None:
    email = settings.ADMIN_EMAIL
    password = settings.ADMIN_PASSWORD
    if not email or not password:
        return
    if not password_policy_ok(password):
        print("[WARN] Seed admin not created: ADMIN_PASSWORD fails password policy")
        return
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role != UserRole.admin or not existing.email_verified:
                existing.role = UserRole.admin
                existing.email_verified = True
                db.add(existing)
                db.commit()
            return
        admin_user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
            email_verified=True,
        )
        db.add(admin_user)
        db.commit()
        print(f"[INFO] Seed admin created: {email}")
    finally:
        db.close()


ensure_seed_admin()

# -------------------------------
# 🚀 Create FastAPI app
# -------------------------------
app = FastAPI(title=settings.APP_NAME)

# -------------------------------
# 🚀 CORS – MUST come before CSRF
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # set in settings.py
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Serve uploaded files
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# -------------------------------
# 🚀 Rate limit middleware
# -------------------------------
@app.middleware("http")
async def _rate_limit(request, call_next):
    await rate_limit(request)
    return await call_next(request)

# -------------------------------
# 🚀 CSRF Middleware (updated)
# -------------------------------
@app.middleware("http")
async def _csrf(request, call_next):
    path = request.url.path

    # Allow OPTIONS always (fix 400 preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    # Routes that do NOT require CSRF
    CSRF_EXEMPT = (
        path.endswith("/auth/csrf")
        or path.startswith("/auth/login")
        or path.startswith("/auth/signup")
        or path.startswith("/auth/verify-email")
        or path.startswith("/auth/reset")
        or path.startswith("/auth/logout")
        or request.method in ("GET", "HEAD")
    )

    if CSRF_EXEMPT:
        return await call_next(request)

    # Real CSRF enforcement
    try:
        csrf_protect(request)
    except Exception as exc:
        from fastapi.responses import JSONResponse
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            return JSONResponse(s
