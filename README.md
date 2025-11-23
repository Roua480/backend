# PolyLab Backend (FastAPI)

## Prerequisites
- Python 3.10+
- SQLite (default) or another SQLAlchemy-supported DB

## Setup
From repo root:
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r Backend/requirements.txt
```

## Environment
Uses repo-root `.env`. Key values:
- `DATABASE_URL` (default `sqlite:///./auth.db`)
- `FRONTEND_ORIGIN` (default `http://localhost:5173`)
- `CORS_ORIGINS` (comma list JSON) e.g. `["http://localhost:5173","http://127.0.0.1:5173"]`
- `BACKEND_BASE_URL` for email links (default `http://localhost:8000`)
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` to seed an admin at startup
- `HSTS_ENABLED`, `RATE_LIMIT_PER_MINUTE`
- SMTP values for email verification/reset (optional; prints links in dev)

## Run
```
uvicorn Backend.main:app --reload --host 0.0.0.0 --port 8000
```
Health: `GET /health`  
Docs: `http://127.0.0.1:8000/docs`

## Security highlights
- Sessions: HttpOnly cookies, SameSite=Lax, Secure when `DEBUG=False`.
- CSRF: double-submit cookie (`csrf_token`) validated on unsafe methods. Exempt only login/signup/verify/reset/logout/auth/csrf.
- MFA TOTP: enroll at `/auth/mfa/totp/enroll`, verify to activate, disable with code. Login enforces TOTP only when `totp_enabled` + secret present.
- Rate limit: per-IP, 60s window (`RATE_LIMIT_PER_MINUTE`).
