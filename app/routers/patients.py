import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import (
    get_current_user,
    require_admin,
    require_doctor_or_admin,
    verify_doctor_patient_access,
)
from app.core.security import get_password_hash
from app.models.consultation import Consultation
from app.models.doctor_patient import DoctorPatient
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User
from app.models.vital_signs import VitalSigns
from app.schemas.consultation import ConsultationOut
from app.schemas.patient import AssignDoctor, PatientCreate, PatientInvite, PatientOut
from app.schemas.prescription import PrescriptionOut
from app.schemas.vital_signs import VitalSignsOut
from app.services.email_service import send_activation_email

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    patient = Patient(
        user_id=None,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        phone=payload.phone,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/{patient_id}/invite")
def invite_patient(
    patient_id: UUID,
    payload: PatientInvite,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """Invitar a un paciente a activar su cuenta. Crea User con rol patient y envía correo con enlace."""
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    check_doctor_patient_access(patient_id, db, current_user)

    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")

    if patient.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient already has an account",
        )

    existing_user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(hours=48)

    user = User(
        email=email,
        password_hash=get_password_hash(secrets.token_urlsafe(32)),
        role="patient",
        is_active=False,
        must_change_password=False,
        activation_token=token,
        activation_token_expires_at=expires_at,
    )
    db.add(user)
    db.flush()
    patient.user_id = user.id
    patient.email = email
    db.add(patient)
    db.commit()

    activation_link = f"{settings.FRONTEND_URL.rstrip('/')}/activate-account?token={token}"
    patient_name = f"{patient.first_name} {patient.last_name}".strip() or "Paciente"
    background_tasks.add_task(
        send_activation_email,
        to_email=email,
        patient_name=patient_name,
        activation_link=activation_link,
    )

    return {"message": "Invitation sent", "email": email}


@router.post("/{patient_id}/assign")
def assign_patient_to_doctor(
    patient_id: UUID,
    payload: AssignDoctor,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    doctor = db.execute(select(User).where(User.id == payload.doctor_id)).scalar_one_or_none()
    if not doctor or doctor.role != "doctor":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid doctor")
    existing = db.execute(
        select(DoctorPatient).where(
            DoctorPatient.doctor_id == payload.doctor_id,
            DoctorPatient.patient_id == patient_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient already assigned to this doctor",
        )
    link = DoctorPatient(doctor_id=payload.doctor_id, patient_id=patient_id)
    db.add(link)
    db.commit()
    return {"message": "Patient assigned to doctor successfully"}


@router.get("/{patient_id}/prescriptions")
def list_patient_prescriptions(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_doctor_patient_access),
):
    stmt = (
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
    )
    if current_user.role == "doctor":
        stmt = stmt.where(Prescription.doctor_id == current_user.id)
    stmt = (
        stmt.order_by(Prescription.created_at.desc())
        .options(selectinload(Prescription.consultation), selectinload(Prescription.items))
    )
    result = db.execute(stmt).scalars().all()
    prescriptions = list(result)
    return [
        {
            **PrescriptionOut.model_validate(p).model_dump(),
            "diagnosis": p.consultation.diagnosis if p.consultation else None,
        }
        for p in prescriptions
    ]


@router.get("/{patient_id}/clinical-history")
def get_patient_clinical_history(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_doctor_patient_access),
):
    stmt = (
        select(Consultation)
        .where(Consultation.patient_id == patient_id)
        .order_by(Consultation.date.desc())
        .options(selectinload(Consultation.vital_signs))
    )
    if current_user.role == "doctor":
        stmt = stmt.where(Consultation.doctor_id == current_user.id)
    consultations = db.execute(stmt).scalars().all()
    return [
        {
            "consultation": ConsultationOut.model_validate(c),
            "vital_signs": VitalSignsOut.model_validate(c.vital_signs) if c.vital_signs else None,
            "diagnosis": c.diagnosis,
            "date": c.date.isoformat() if c.date else None,
        }
        for c in consultations
    ]


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(verify_doctor_patient_access),
):
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient
