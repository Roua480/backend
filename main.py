from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Absolute imports (Render requires this)
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


# -------------------------------
# DB Setup
# -------------------------------
Base.metadata.create_all(bind=engine)


# -------------------------------
# Seed Admin
# -------------------------------
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
# Create App
# -------------------------------
app = FastAPI(title=settings.APP_NAME)


# -------------------------------
# CORS
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)


# -------------------------------
# Static Uploads Directory
# -------------------------------
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# -------------------------------
# Rate Limit Middleware
# -------------------------------
@app.middleware("http")
async def _rate_limit(request, call_next):
    await rate_limit(request)
    return await call_next(request)


# -------------------------------
# CSRF Middleware
# -------------------------------
@app.middleware("http")
async def _csrf(request, call_next):
    path = request.url.path

    if (
        request.method in ("GET", "HEAD", "OPTIONS")
        or path.endswith("/auth/csrf")
        or path.startswith("/auth/login")
        or path.startswith("/auth/signup")
        or path.startswith("/auth/verify-email")
        or path.startswith("/auth/reset")
        or path.startswith("/auth/logout")
    ):
        return await call_next(request)

    try:
        csrf_protect(request)
    except Exception as exc:
        from fastapi.responses import JSONResponse
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )

        return JSONResponse(status_code=403, content={"detail": "CSRF check failed"})

    return await call_next(request)


# -------------------------------
# Routers
# -------------------------------
app.include_router(auth.router)
app.include_router(mfa.router)
app.include_router(me.router)
app.include_router(instructor_requests.router)
app.include_router(classrooms.router)
app.include_router(assignment.router)
app.include_router(materials.router)
app.include_router(quiz.router)
app.include_router(submission.router)
app.include_router(admin.router)


# -------------------------------
# Health Check
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"status": "ok"}
