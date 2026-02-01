import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import require_doctor
from app.models.doctor_profile import DoctorProfile
from app.models.user import User
from app.schemas.doctor_profile import DoctorProfileOut, DoctorProfileUpdate

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg"}
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB

router = APIRouter(prefix="/doctor-profile", tags=["doctor-profile"])


def _safe_filename(filename: str | None) -> str:
    if not filename or not filename.strip():
        return "file"
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", filename.strip())


def _get_or_create_profile(db: Session, user_id) -> DoctorProfile:
    profile = db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == user_id)
    ).scalar_one_or_none()
    if profile is None:
        profile = DoctorProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/me", response_model=DoctorProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    profile = _get_or_create_profile(db, current_user.id)
    return profile


@router.put("/me", response_model=DoctorProfileOut)
def update_my_profile(
    payload: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    profile = _get_or_create_profile(db, current_user.id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/upload-signature")
async def upload_signature(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Formato inválido. Use PNG o JPEG.")
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Imagen demasiado grande (máx 2MB)",
        )
    _safe_filename(file.filename or "")

    doctor_folder = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(doctor_folder, exist_ok=True)
    ext = "png" if file.content_type == "image/png" else "jpg"
    filepath = os.path.join(doctor_folder, f"firma.{ext}")

    profile = _get_or_create_profile(db, current_user.id)
    if profile.signature_url:
        old_path = os.path.normpath(profile.signature_url)
        if os.path.exists(old_path):
            os.remove(old_path)

    with open(filepath, "wb") as buffer:
        buffer.write(contents)

    url_path = f"{settings.UPLOAD_DIR}/{current_user.id}/firma.{ext}".replace("\\", "/")
    profile.signature_url = url_path
    db.add(profile)
    db.commit()
    return {"message": "Firma subida correctamente", "url": url_path}


@router.post("/upload-stamp")
async def upload_stamp(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Formato inválido. Use PNG o JPEG.")
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Imagen demasiado grande (máx 2MB)",
        )
    _safe_filename(file.filename or "")

    doctor_folder = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(doctor_folder, exist_ok=True)
    ext = "png" if file.content_type == "image/png" else "jpg"
    filepath = os.path.join(doctor_folder, f"sello.{ext}")

    profile = _get_or_create_profile(db, current_user.id)
    if profile.stamp_url:
        old_path = os.path.normpath(profile.stamp_url)
        if os.path.exists(old_path):
            os.remove(old_path)

    with open(filepath, "wb") as buffer:
        buffer.write(contents)

    url_path = f"{settings.UPLOAD_DIR}/{current_user.id}/sello.{ext}".replace("\\", "/")
    profile.stamp_url = url_path
    db.add(profile)
    db.commit()
    return {"message": "Sello subido correctamente", "url": url_path}
