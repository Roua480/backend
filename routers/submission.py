from datetime import datetime
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_instructor
from ..core.config import settings

router = APIRouter(prefix="/submissions", tags=["Submissions"])


def _get_assignment(db: Session, assignment_id: int) -> models.Assignment:
    assignment = db.query(models.Assignment).filter_by(id=assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _ensure_membership(
    db: Session, classroom_id: int, user: models.User, *, allow_instructor=True
):
    if user.role == models.UserRole.admin:
        return
    classroom = db.query(models.Classroom).filter_by(id=classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    if allow_instructor and classroom.instructor_id == user.id:
        return
    member = (
        db.query(models.ClassroomMember)
        .filter_by(classroom_id=classroom_id, user_id=user.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")


@router.post("/", response_model=schemas.SubmissionOut)
def create_submission(
    payload: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    assignment = _get_assignment(db, payload.assignment_id)
    if assignment.due_date and datetime.utcnow() > assignment.due_date:
        raise HTTPException(status_code=400, detail="Past due date")
    _ensure_membership(db, assignment.classroom_id, user)
    submission = models.Submission(
        user_id=user.id, assignment_id=assignment.id, content=payload.content
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/assignment/{assignment_id}", response_model=list[schemas.SubmissionWithUser])
def list_submissions_for_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    assignment = _get_assignment(db, assignment_id)
    classroom = assignment.classroom
    if user.role == models.UserRole.admin or classroom.instructor_id == user.id:
        submissions = (
            db.query(models.Submission)
            .filter(models.Submission.assignment_id == assignment_id)
            .order_by(models.Submission.user_id, models.Submission.submitted_at.desc(), models.Submission.id.desc())
            .all()
        )
        latest: dict[int, models.Submission] = {}
        for sub in submissions:
            if sub.user_id not in latest:
                latest[sub.user_id] = sub
        return [
            schemas.SubmissionWithUser(
                **schemas.SubmissionOut.model_validate(sub, from_attributes=True).model_dump(),
                user_email=sub.user.email,
            )
            for sub in latest.values()
        ]
    _ensure_membership(db, assignment.classroom_id, user, allow_instructor=False)
    submissions = (
        db.query(models.Submission)
        .filter_by(assignment_id=assignment_id, user_id=user.id)
        .order_by(models.Submission.submitted_at.desc())
        .all()
    )
    return [
        schemas.SubmissionWithUser(
            **schemas.SubmissionOut.model_validate(sub, from_attributes=True).model_dump(),
            user_email=sub.user.email,
        )
        for sub in submissions
    ]


@router.get("/classroom/{classroom_id}", response_model=list[schemas.SubmissionWithUser])
def list_submissions_for_classroom(
    classroom_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    _ensure_membership(db, classroom_id, user)
    submissions = (
        db.query(models.Submission)
        .join(models.Assignment, models.Submission.assignment_id == models.Assignment.id)
        .filter(models.Assignment.classroom_id == classroom_id)
        .order_by(
            models.Submission.assignment_id,
            models.Submission.user_id,
            models.Submission.submitted_at.desc(),
            models.Submission.id.desc(),
        )
        .all()
    )
    latest: dict[tuple[int, int], models.Submission] = {}
    for sub in submissions:
        key = (sub.assignment_id, sub.user_id)
        if key not in latest:
            latest[key] = sub
    return [
        schemas.SubmissionWithUser(
            **schemas.SubmissionOut.model_validate(sub, from_attributes=True).model_dump(),
            user_email=sub.user.email,
        )
        for sub in latest.values()
    ]


@router.post("/{assignment_id}/upload", response_model=schemas.SubmissionOut)
async def upload_submission_file(
    assignment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    assignment = _get_assignment(db, assignment_id)
    _ensure_membership(db, assignment.classroom_id, user)

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "upload.bin")
    base_dir = Path(settings.UPLOAD_DIR) / "submissions" / f"assignment_{assignment_id}"
    base_dir.mkdir(parents=True, exist_ok=True)
    dest = base_dir / f"user{user.id}_{int(datetime.utcnow().timestamp())}_{safe_name}"

    content = await file.read()
    dest.write_bytes(content)

    submission = models.Submission(
        user_id=user.id,
        assignment_id=assignment.id,
        content=str(dest),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.post("/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    grade: float,
    db: Session = Depends(get_db),
    instructor=Depends(require_instructor),
):
    submission = (
        db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    assignment = submission.assignment
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_membership(db, assignment.classroom_id, instructor, allow_instructor=True)
    submission.grade = grade
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"ok": True, "grade": submission.grade}
