from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_instructor

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


def _ensure_can_manage(classroom: models.Classroom, user: models.User):
    if user.role == models.UserRole.admin:
        return
    if classroom.instructor_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed for this classroom")


def _get_quiz(db: Session, quiz_id: int) -> models.Quiz:
    quiz = db.query(models.Quiz).filter_by(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.post("/", response_model=schemas.QuizOut)
def create_quiz(
    payload: schemas.QuizCreate,
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    classroom = db.query(models.Classroom).filter_by(id=payload.classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    _ensure_can_manage(classroom, user)
    quiz = models.Quiz(**payload.dict())
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


@router.get("/{quiz_id}", response_model=schemas.QuizOut)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return _get_quiz(db, quiz_id)


@router.put("/{quiz_id}", response_model=schemas.QuizOut)
def update_quiz(
    quiz_id: int,
    payload: schemas.QuizCreate,
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    quiz = _get_quiz(db, quiz_id)
    _ensure_can_manage(quiz.classroom, user)
    for key, value in payload.dict().items():
        setattr(quiz, key, value)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


@router.delete("/{quiz_id}")
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    quiz = _get_quiz(db, quiz_id)
    _ensure_can_manage(quiz.classroom, user)
    db.delete(quiz)
    db.commit()
    return {"ok": True}

