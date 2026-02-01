"""Pacientes del médico: crear, listar, buscar, ver detalle."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import check_doctor_patient_access, get_current_doctor
from app.models.consultation import Consultation
from app.models.doctor_patient import DoctorPatient
from app.models.patient import Patient
from app.models.user import User
from app.utils.subscription_limits import check_patient_limit
from app.schemas.patient import (
    ConsultationSummaryOut,
    DoctorPatientCreate,
    PatientDetailOut,
    PatientHistoryUpdate,
    PatientOut,
)

router = APIRouter(prefix="/patients", tags=["doctor-patients"])


def _patient_belongs_to_doctor(patient: Patient, doctor_id: UUID) -> bool:
    return patient.doctor_id == doctor_id or any(
        dp.doctor_id == doctor_id for dp in (patient.doctors or [])
    )


def _list_patients_query(doctor_id: UUID):
    """Pacientes del médico: doctor_id = médico O enlace DoctorPatient."""
    return (
        select(Patient)
        .where(
            or_(
                Patient.doctor_id == doctor_id,
                Patient.id.in_(
                    select(DoctorPatient.patient_id).where(
                        DoctorPatient.doctor_id == doctor_id
                    )
                ),
            )
        )
        .distinct()
    )


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: DoctorPatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Crear un nuevo paciente. El doctor_id se toma del usuario autenticado."""
    check_patient_limit(db, current_user.id)
    patient = Patient(
        doctor_id=current_user.id,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        dni=payload.dni.strip() if payload.dni else None,
        date_of_birth=payload.birth_date,
        sex=payload.sex.strip() if payload.sex else None,
        phone=payload.phone.strip() if payload.phone else None,
        email=payload.email.strip() if payload.email else None,
        address=payload.address.strip() if payload.address else None,
        province=payload.province.strip() if payload.province else None,
        city=payload.city.strip() if payload.city else None,
        anamnesis=payload.anamnesis.strip() if payload.anamnesis else None,
        personal_history=payload.personal_history.strip() if payload.personal_history else None,
        allergic_history=payload.allergic_history.strip() if payload.allergic_history else None,
        gyneco_history=payload.gyneco_history.strip() if payload.gyneco_history else None,
        surgical_history=payload.surgical_history.strip() if payload.surgical_history else None,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return PatientOut.model_validate(patient)


@router.get("", response_model=list[PatientOut])
def list_my_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Listar solo los pacientes de este médico (doctor_id o DoctorPatient)."""
    stmt = _list_patients_query(current_user.id).order_by(
        Patient.last_name, Patient.first_name
    )
    patients = db.execute(stmt).scalars().all()
    return [PatientOut.model_validate(p) for p in patients]


@router.get("/search", response_model=list[PatientOut])
def search_patients(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Buscar pacientes por nombre, apellido o nombre completo (solo del médico)."""
    q_clean = q.strip()
    stmt = (
        _list_patients_query(current_user.id)
        .where(
            or_(
                Patient.first_name.ilike(f"%{q_clean}%"),
                Patient.last_name.ilike(f"%{q_clean}%"),
                # Búsqueda en nombre completo concatenado
                (Patient.first_name + " " + Patient.last_name).ilike(f"%{q_clean}%"),
            )
        )
        .order_by(Patient.last_name, Patient.first_name)
        .limit(limit)
    )
    patients = db.execute(stmt).scalars().all()
    return [PatientOut.model_validate(p) for p in patients]


@router.get("/{patient_id}", response_model=PatientDetailOut)
def get_patient_detail(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Ver detalle del paciente e historial de consultas. Solo si pertenece al médico."""
    check_doctor_patient_access(patient_id, db, current_user)
    patient = db.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .options(selectinload(Patient.consultations))
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    consultations = (
        db.execute(
            select(Consultation)
            .where(Consultation.patient_id == patient_id)
            .order_by(Consultation.date.desc())
        )
        .scalars().all()
    )
    return PatientDetailOut(
        **PatientOut.model_validate(patient).model_dump(),
        consultations=[
            ConsultationSummaryOut(
                id=c.id,
                date=c.date,
                diagnosis_main=c.diagnosis_main,
                diagnosis_secondary=c.diagnosis_secondary,
            )
            for c in consultations
        ],
    )


@router.patch("/{patient_id}/history", response_model=PatientOut)
def update_patient_history(
    patient_id: UUID,
    payload: PatientHistoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Actualizar antecedentes del paciente (solo campos clínicos base)."""
    check_doctor_patient_access(patient_id, db, current_user)
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value.strip() if isinstance(value, str) and value else value)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return PatientOut.model_validate(patient)
