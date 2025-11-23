from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..models import User
from ..schemas import UserOut

router = APIRouter(prefix="/me", tags=["Me"])


@router.get("", response_model=UserOut)
def read_profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "email_verified": user.email_verified,
        "totp_enabled": bool(user.totp_enabled and user.totp_secret),
    }

