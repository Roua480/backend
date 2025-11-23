from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_instructor
from ..core.config import settings

router = APIRouter(prefix="/materials", tags=["Materials"])


def _ensure_classroom(db: Session, classroom_id: int) -> models.Classroom:
    classroom = db.query(models.Classroom).filter_by(id=classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return classroom


@router.get("/classroom/{classroom_id}", response_model=list[schemas.MaterialOut])
def list_materials(
    classroom_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # membership check: students must belong; instructors/admin allowed
    classroom = _ensure_classroom(db, classroom_id)
    if user.role not in (models.UserRole.admin, models.UserRole.instructor):
        member = (
            db.query(models.ClassroomMember)
            .filter_by(classroom_id=classroom_id, user_id=user.id)
            .first()
        )
        if not member:
            raise HTTPException(status_code=403, detail="You are not enrolled in this class")
    materials = (
        db.query(models.Material)
        .filter_by(classroom_id=classroom_id)
        .order_by(models.Material.created_at.desc())
        .all()
    )
    return materials


@router.post("/", response_model=schemas.MaterialOut)
async def create_material(
    payload: schemas.MaterialCreate,
    db: Session = Depends(get_db),
    instructor=Depends(require_instructor),
):
    classroom = _ensure_classroom(db, payload.classroom_id)
    if classroom.instructor_id != instructor.id and instructor.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Not allowed for this classroom")
    material = models.Material(**payload.dict())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.post("/{material_id}/upload", response_model=schemas.MaterialOut)
async def upload_material(
    material_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    instructor=Depends(require_instructor),
):
    material = db.query(models.Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    classroom = _ensure_classroom(db, material.classroom_id)
    if classroom.instructor_id != instructor.id and instructor.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Not allowed for this classroom")

    base_dir = Path(settings.UPLOAD_DIR) / "materials" / f"classroom_{material.classroom_id}"
    base_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".", " ") else "_" for ch in (file.filename or "material.pdf"))
    dest = base_dir / safe_name
    content = await file.read()
    dest.write_bytes(content)
    material.file_url = f"/uploads/materials/classroom_{material.classroom_id}/{safe_name}"
    db.add(material)
    db.commit()
    db.refresh(material)
    return material
