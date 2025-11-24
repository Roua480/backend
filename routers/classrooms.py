import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import get_current_user, require_instructor


router = APIRouter(prefix="/classrooms", tags=["Classrooms"])


def _generate_code(db: Session) -> str:
    for _ in range(5):
        code = secrets.token_hex(3).upper()
        exists = db.query(models.Classroom).filter(models.Classroom.code == code).first()
        if not exists:
            return code
    raise RuntimeError("Unable to generate unique classroom code")


@router.post("/", response_model=schemas.ClassroomOut)
def create_classroom(
    payload: schemas.ClassroomCreate,
    db: Session = Depends(get_db),
    instructor=Depends(require_instructor),
):
    code = _generate_code(db)
    classroom = models.Classroom(
        name=payload.name,
        code=code,
        instructor_id=instructor.id,
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    # Instructor automatically joins their classroom
    db.add(models.ClassroomMember(classroom_id=classroom.id, user_id=instructor.id))
    db.commit()
    return classroom


@router.post("/join", response_model=schemas.BasicOK)
def join_classroom(
    payload: schemas.JoinClassroomRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    classroom = db.query(models.Classroom).filter_by(code=payload.code).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Invalid classroom code")
    membership = (
        db.query(models.ClassroomMember)
        .filter_by(classroom_id=classroom.id, user_id=user.id)
        .first()
    )
    if membership:
        return {"ok": True}
    db.add(models.ClassroomMember(classroom_id=classroom.id, user_id=user.id))
    db.commit()
    return {"ok": True}


@router.get("/", response_model=list[schemas.ClassroomOut])
def list_classrooms(
    db: Session = Depends(get_db), user=Depends(get_current_user)
):
    owned = db.query(models.Classroom).filter_by(instructor_id=user.id).all()
    member = (
        db.query(models.Classroom)
        .join(
            models.ClassroomMember,
            models.Classroom.id == models.ClassroomMember.classroom_id,
        )
        .filter(models.ClassroomMember.user_id == user.id)
        .all()
    )
    dedup = {cls.id: cls for cls in [*owned, *member]}
    return list(dedup.values())
