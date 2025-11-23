from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr

from .models import UserRole


class OrmBase(BaseModel):
    class Config:
        from_attributes = True


class SignupIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    totp: str | None = None


class UserOut(OrmBase):
    id: int
    email: EmailStr
    role: UserRole
    email_verified: bool
    totp_enabled: bool


class BasicOK(BaseModel):
    ok: bool = True


class ClassroomCreate(BaseModel):
    name: str


class ClassroomOut(OrmBase):
    id: int
    name: str
    code: str
    instructor_id: int
    created_at: datetime


class JoinClassroomRequest(BaseModel):
    code: str


class InstructorRequestOut(OrmBase):
    id: int
    status: Literal["pending", "approved", "rejected"]
    note: Optional[str] = None
    file_path: str
    user_id: int
    created_at: datetime


class InstructorRequestAdminOut(InstructorRequestOut):
    user_email: Optional[EmailStr] = None
    decision_by: Optional[int] = None
    decided_at: Optional[datetime] = None


class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    classroom_id: int
    due_date: Optional[datetime] = None
    attachment_url: Optional[str] = None


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentOut(AssignmentBase, OrmBase):
    id: int
    created_at: datetime


class AssignmentTemplate(BaseModel):
    id: str
    title: str
    description: Optional[str] = None


class QuizBase(BaseModel):
    title: str
    description: Optional[str] = None
    classroom_id: int
    due_date: Optional[datetime] = None


class QuizCreate(QuizBase):
    pass


class QuizOut(QuizBase, OrmBase):
    id: int
    created_at: datetime


class SubmissionCreate(BaseModel):
    assignment_id: int
    content: str


class SubmissionOut(SubmissionCreate, OrmBase):
    id: int
    user_id: int
    grade: Optional[float]
    submitted_at: datetime


class SubmissionWithUser(SubmissionOut):
    user_email: EmailStr


class MaterialBase(BaseModel):
    classroom_id: int
    title: str
    description: Optional[str] = None
    file_url: Optional[str] = None


class MaterialCreate(MaterialBase):
    pass


class MaterialOut(MaterialBase, OrmBase):
    id: int
    created_at: datetime


class MFAEnrollOut(BaseModel):
    secret: str
    otpauth: str
    mfa_token: str


class MFAVerifyIn(BaseModel):
    code: str
    mfa_token: str | None = None
