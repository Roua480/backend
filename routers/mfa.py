from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import BasicOK, MFAEnrollOut, MFAVerifyIn
from ..utils.tokens import consume_token, make_token
from ..utils.totp import create_totp_secret, make_otpauth_uri, verify_totp

router = APIRouter(prefix="/auth/mfa/totp", tags=["MFA"])


@router.post("/enroll", response_model=MFAEnrollOut)
def enroll(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    secret = create_totp_secret()
    # store as pending until verification succeeds
    user.pending_totp_secret = secret
    db.add(user)
    db.commit()
    token = make_token(db, user, "mfa", minutes=10)
    return MFAEnrollOut(
        secret=secret,
        otpauth=make_otpauth_uri(secret, user.email, "PolyLab"),
        mfa_token=token,
    )


@router.post("/verify", response_model=BasicOK)
def verify(body: MFAVerifyIn, db: Session = Depends(get_db)):
    if not body.mfa_token:
        raise HTTPException(status_code=400, detail="MFA token required")
    user = consume_token(db, body.mfa_token, "mfa")
    if not user:
        raise HTTPException(status_code=400, detail="Invalid MFA token")
    if not user.pending_totp_secret:
        raise HTTPException(status_code=400, detail="No MFA setup in progress")
    if not verify_totp(user.pending_totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    # promote pending secret to active and mark enabled
    user.totp_secret = user.pending_totp_secret
    user.pending_totp_secret = None
    user.totp_enabled = True
    db.add(user)
    db.commit()
    return {"ok": True}


@router.post("/disable", response_model=BasicOK)
def disable(
    body: MFAVerifyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.totp_secret and not user.pending_totp_secret:
        return {"ok": True}
    if user.totp_secret:
        if not body.code or not verify_totp(user.totp_secret, body.code):
            raise HTTPException(status_code=400, detail="Invalid code")
    user.totp_secret = None
    user.pending_totp_secret = None
    user.totp_enabled = False
    db.add(user)
    db.commit()
    return {"ok": True}

