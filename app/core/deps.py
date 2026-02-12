from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models.consultation import Consultation
from app.models.doctor_patient import DoctorPatient
from app.models.prescription import Prescription
from app.models.patient import Patient
from app.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        token = request.cookies.get("rf_access_token")
    if not token and request.headers.get("authorization"):
        auth = request.headers["authorization"]
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.execute(select(User).where(User.id == user_uuid)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

    if user.role == "doctor" and getattr(user, "must_change_password", False):
        allowed_paths = {"/auth/change-password", "/auth/me", "/auth/logout"}
        if request.url.path not in allowed_paths:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required",
            )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user


def require_doctor(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor only")
    return current_user


def require_patient(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient only")
    return current_user


def require_doctor_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("doctor", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor or admin only")
    return current_user


# Alias por rol para rutas /admin/*, /doctor/*, /patient/* (misma lógica que require_*)
get_current_admin = require_admin
get_current_doctor = require_doctor
get_current_patient = require_patient


def check_doctor_patient_access(patient_id: UUID, db: Session, current_user: User) -> None:
    """Raises HTTPException 403 if current_user does not have access to the patient."""
    if current_user.role == "admin":
        return
    if current_user.role == "doctor":
        patient = db.execute(
            select(Patient).where(Patient.id == patient_id)
        ).scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        if patient.doctor_id == current_user.id:
            return
        link = db.execute(
            select(DoctorPatient).where(
                DoctorPatient.doctor_id == current_user.id,
                DoctorPatient.patient_id == patient_id,
            )
        ).scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    if current_user.role == "patient":
        patient = db.execute(
            select(Patient).where(Patient.id == patient_id)
        ).scalar_one_or_none()
        if not patient or patient.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def verify_doctor_patient_access(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    check_doctor_patient_access(patient_id, db, current_user)


def verify_consultation_access(
    consultation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Consultation:
    consultation = db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    ).scalar_one_or_none()
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    if current_user.role == "admin":
        return consultation
    if current_user.role == "doctor" and consultation.doctor_id == current_user.id:
        return consultation
    if current_user.role == "patient":
        patient = db.execute(
            select(Patient).where(Patient.id == consultation.patient_id)
        ).scalar_one_or_none()
        if patient and patient.user_id == current_user.id:
            return consultation
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def verify_prescription_access(
    prescription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Prescription:
    prescription = db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    ).scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    if current_user.role == "admin":
        return prescription
    if current_user.role == "doctor" and prescription.doctor_id == current_user.id:
        return prescription
    if current_user.role == "patient":
        patient = db.execute(
            select(Patient).where(Patient.id == prescription.patient_id)
        ).scalar_one_or_none()
        if patient and patient.user_id == current_user.id:
            return prescription
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
