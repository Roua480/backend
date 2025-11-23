import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import Token, User


def make_token(db: Session, user: User, purpose: str, minutes: int) -> str:
    value = secrets.token_urlsafe(32)
    db.add(
        Token(
            user_id=user.id,
            token=value,
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=minutes),
        )
    )
    db.commit()
    return value


def consume_token(db: Session, token: str, purpose: str) -> User | None:
    row = (
        db.query(Token)
        .filter(Token.token == token, Token.purpose == purpose)
        .first()
    )
    if not row or row.expires_at < datetime.utcnow():
        return None
    user = db.query(User).filter(User.id == row.user_id).first()
    db.delete(row)
    db.commit()
    return user

