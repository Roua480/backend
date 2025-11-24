from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.csrf import issue_csrf
from core.security import (
    clear_session_cookie,
    create_session,
    hash_password,
    password_policy_ok,
    set_session_cookie,
    verify_password,
)
from database import get_db
from models import Session as DBSession
from models import User
from schemas import BasicOK, LoginIn, SignupIn
from utils.email import send_reset_email, send_verification_email
from utils.tokens import consume_token
from utils.totp import verify_totp


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/csrf")
def get_csrf(response: Response) -> dict:
    token = issue_csrf(response)
    return {"csrf": token}


@router.post("/signup", response_model=BasicOK)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    if not password_policy_ok(payload.password):
        raise HTTPException(status_code=400, detail="Weak password")
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    send_verification_email(db, user)
    return {"ok": True}


def _verify_email_token(token: str, db: Session) -> None:
    user = consume_token(db, token, "verify")
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.email_verified = True
    db.add(user)
    db.commit()


@router.post("/verify-email", response_model=BasicOK)
def verify_email(token: str, db: Session = Depends(get_db)):
    _verify_email_token(token, db)
    return {"ok": True}


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_page(token: str, db: Session = Depends(get_db)):
    _verify_email_token(token, db)
    if settings.FRONTEND_ORIGIN:
        target = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/verify?token={token}&status=verified"
        return RedirectResponse(target, status_code=307)
    # Fallback minimal page if no frontend origin is configured
    return """
    <html>
      <head><title>Email verified</title></head>
      <body style="font-family: system-ui; text-align:center; margin-top:4rem;">
        <h1>Email verified</h1>
        <p>You can now return to PolyLab and log in.</p>
      </body>
    </html>
    """


@router.post("/login", response_model=BasicOK)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")
    if user.totp_enabled and user.totp_secret:
        if not payload.totp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA TOTP required")
        if not verify_totp(user.totp_secret, payload.totp):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")
    sid = create_session(db, user)
    set_session_cookie(response, sid)
    issue_csrf(response)
    return {"ok": True}


@router.post("/logout", response_model=BasicOK)
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if sid:
        db.query(DBSession).filter(DBSession.id == sid).delete()
        db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.post("/reset", response_model=BasicOK)
def reset_start(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        send_reset_email(db, user)
    return {"ok": True}


@router.get("/reset/confirm", response_class=HTMLResponse)
def reset_confirm_page(token: str):
    if settings.FRONTEND_ORIGIN:
        target = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/reset/confirm?token={token}"
        return RedirectResponse(target, status_code=307)
    return f"""
    <html>
      <head><title>Reset password</title></head>
      <body style="font-family: system-ui; text-align:center; margin-top:3rem;">
        <h1>Reset your password</h1>
        <p>Enter a new password to finish resetting your account.</p>
        <form method="post" action="/auth/reset/confirm">
          <input type="hidden" name="token" value="{token}" />
          <input type="password" name="new_password" placeholder="New password" required
                 style="padding:0.5rem 0.75rem; width:260px;" />
          <div style="margin-top:1rem;">
            <button type="submit" style="padding:0.5rem 1rem;">Update password</button>
          </div>
        </form>
      </body>
    </html>
    """


@router.post("/reset/confirm", response_model=BasicOK)
def reset_confirm(
    request: Request,
    token: str | None = Form(default=None),
    new_password: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    token = token or request.query_params.get("token")
    new_password = new_password or request.query_params.get("new_password")
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new_password are required")
    if not password_policy_ok(new_password):
        raise HTTPException(status_code=400, detail="Weak password")
    user = consume_token(db, token, "reset")
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    return {"ok": True}

