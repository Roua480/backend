import secrets
import uuid
from datetime import datetime, timedelta
from typing import Iterable, Sequence

from fastapi import Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import Session as DBSession
from models import User, UserRole
from core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.SESSION_TTL_MINUTES * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
    )


def create_session(db: Session, user: User) -> str:
    now = datetime.utcnow()
    sid = str(uuid.uuid4())
    expires = now + timedelta(minutes=settings.SESSION_TTL_MINUTES)
    # Optionally prune expired sessions for this user
    db.query(DBSession).filter(
        DBSession.user_id == user.id, DBSession.expires_at < now
    ).delete()
    db.add(
        DBSession(
            id=sid,
            user_id=user.id,
            created_at=now,
            expires_at=expires,
        )
    )
    db.commit()
    return sid


def _normalize_roles(roles: Sequence[str | UserRole]) -> set[str]:
    normalized: set[str] = set()
    for role in roles:
        normalized.add(role.value if isinstance(role, UserRole) else role)
    return normalized


def require_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    sid = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not sid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    session = db.query(DBSession).filter(DBSession.id == sid).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def require_role(*roles: str | UserRole):
    allowed = _normalize_roles(roles or (UserRole.student,))

    def _dep(user: User = Depends(require_user)) -> User:
        user_role = user.role.value if isinstance(user.role, UserRole) else user.role
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return user

    return _dep


PASSWORD_POLICY = {
    "min_len": 8,
    "max_len": 256,
    "require_upper": True,
    "require_lower": True,
    "require_digit": True,
    "require_symbol": True,
}


def password_policy_ok(password: str) -> bool:
    if len(password) < PASSWORD_POLICY["min_len"]:
        return False
    if len(password) > PASSWORD_POLICY["max_len"]:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    checks = [
        has_upper if PASSWORD_POLICY["require_upper"] else True,
        has_lower if PASSWORD_POLICY["require_lower"] else True,
        has_digit if PASSWORD_POLICY["require_digit"] else True,
        has_symbol if PASSWORD_POLICY["require_symbol"] else True,
    ]
    return all(checks)

