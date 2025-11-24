from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import text
from sqlalchemy.orm import Session

from models import models, schemas
from database import get_db
from deps import get_current_user, require_instructor
from core.config import settings

router = APIRouter(prefix="/assignments", tags=["Assignments"])

POLY_TEMPLATES: list[schemas.AssignmentTemplate] = [
    schemas.AssignmentTemplate(
        id="gf-addition",
        title="Polynomial Addition in GF(2)",
        description="Add the following polynomials over GF(2):\n1) x⁴ + x² + 1  +  x³ + x² + x\n2) x⁷ + x + 1  +  x⁶ + x⁵ + x²",
    ),
    schemas.AssignmentTemplate(
        id="gf-multiplication",
        title="Polynomial Multiplication mod (x³ + x + 1)",
        description="Compute (x² + 1) · (x + 1) over GF(2), then reduce modulo the irreducible polynomial x³ + x + 1.",
    ),
    schemas.AssignmentTemplate(
        id="gf-irreducible",
        title="Check Irreducibility",
        description="Show whether x⁴ + x + 1 is irreducible over GF(2). If reducible, factor it; if irreducible, justify briefly.",
    ),
    schemas.AssignmentTemplate(
        id="gf-eval",
        title="Evaluate Polynomial in GF(5)",
        description="Evaluate f(x) = 3x³ + 4x² + 2x + 1 at x = 7 (mod 5). Show intermediate steps.",
    ),
]


def _ensure_can_manage(classroom: models.Classroom, user: models.User):
    if user.role == models.UserRole.admin:
        return
    if classroom.instructor_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed for this classroom")


def _get_assignment(db: Session, assignment_id: int) -> models.Assignment:
    assignment = db.query(models.Assignment).filter_by(id=assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _ensure_membership(db: Session, classroom_id: int, user: models.User):
    if user.role == models.UserRole.admin:
        return
    classroom = db.query(models.Classroom).filter_by(id=classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    if classroom.instructor_id == user.id:
        return
    membership = (
        db.query(models.ClassroomMember)
        .filter_by(classroom_id=classroom_id, user_id=user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")


def _store_attachment(assignment_id: int, filename: str, content: bytes) -> str:
    base_dir = Path(settings.UPLOAD_DIR) / "assignments" / f"assignment_{assignment_id}"
    base_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".", " ") else "_" for ch in (filename or "assignment.pdf"))
    dest = base_dir / safe_name
    dest.write_bytes(content)
    # Return URL path relative to static mount
    return f"/uploads/assignments/assignment_{assignment_id}/{safe_name}"


def _ensure_attachment_column(db: Session) -> None:
    # Adds attachment_url column on existing DBs that predate the change.
    result = db.execute(text("PRAGMA table_info(assignments)")).fetchall()
    has_col = any(row[1] == "attachment_url" for row in result)
    if not has_col:
        db.execute(text("ALTER TABLE assignments ADD COLUMN attachment_url TEXT"))
        db.commit()


@router.get("/classroom/{classroom_id}", response_model=list[schemas.AssignmentOut])
def list_assignments_for_classroom(
    classroom_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ensure_membership(db, classroom_id, user)
    assignments = (
        db.query(models.Assignment)
        .filter(models.Assignment.classroom_id == classroom_id)
        .order_by(models.Assignment.created_at.desc())
        .all()
    )
    return assignments


@router.get("/templates", response_model=list[schemas.AssignmentTemplate])
def list_assignment_templates():
    return POLY_TEMPLATES


@router.post(
    "/",
    response_model=schemas.AssignmentOut,
)
async def create_assignment(
    payload: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    _ensure_attachment_column(db)
    classroom = db.query(models.Classroom).filter_by(id=payload.classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    _ensure_can_manage(classroom, user)
    assignment = models.Assignment(**payload.dict())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post(
    "/{assignment_id}/attachment",
    response_model=schemas.AssignmentOut,
)
async def upload_assignment_attachment(
    assignment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    _ensure_attachment_column(db)
    assignment = _get_assignment(db, assignment_id)
    _ensure_can_manage(assignment.classroom, user)
    content = await file.read()
    attachment_url = _store_attachment(assignment_id, file.filename or "assignment.pdf", content)
    assignment.attachment_url = attachment_url
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/{assignment_id}", response_model=schemas.AssignmentOut)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    assignment = _get_assignment(db, assignment_id)
    return assignment


@router.put(
    "/{assignment_id}",
    response_model=schemas.AssignmentOut,
)
def update_assignment(
    assignment_id: int,
    payload: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    _ensure_attachment_column(db)
    assignment = _get_assignment(db, assignment_id)
    _ensure_can_manage(assignment.classroom, user)
    for key, value in payload.dict().items():
        setattr(assignment, key, value)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_instructor),
):
    assignment = _get_assignment(db, assignment_id)
    _ensure_can_manage(assignment.classroom, user)
    db.delete(assignment)
    db.commit()
    return None
