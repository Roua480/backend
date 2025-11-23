from fastapi import Depends

from .core.security import require_role, require_user
from .database import get_db as _get_db
from .models import User, UserRole


def get_db():
    yield from _get_db()


def get_current_user(user: User = Depends(require_user)) -> User:
    return user


require_admin = require_role(UserRole.admin)
require_instructor = require_role(UserRole.instructor, UserRole.admin)

