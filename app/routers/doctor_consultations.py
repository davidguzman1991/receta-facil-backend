"""Endpoints del portal del médico: Nueva Consulta Médica y medicamentos."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import check_doctor_patient_access, get_current_doctor
from app.models.consultation import Consultation
from app.models.consultation_medication import ConsultationMedication
from app.models.doctor_profile import DoctorProfile
from app.models.drug import Drug
from app.models.patient import Patient
from app.models.user import User
from app.schemas.consultation import DoctorConsultationCreate, DoctorConsultationOut
from app.schemas.drug import ConsultationMedicationCreate, ConsultationMedicationOut

router = APIRouter(prefix="/consultations", tags=["doctor-consultations"])


def _doctor_full_name(db: Session, user_id: UUID) -> str:
    profile = db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == user_id)
    ).scalar_one_or_none()
    if profile and (profile.full_name or (profile.nombres or profile.apellidos)):
        return profile.full_name or f"{(profile.nombres or '').strip()} {(profile.apellidos or '').strip()}".strip() or "Médico"
    return "Médico"


def _consultation_to_out(db: Session, c: Consultation) -> DoctorConsultationOut:
    patient_name = f"{c.patient.first_name} {c.patient.last_name}".strip()
    doctor_name = _doctor_full_name(db, c.doctor_id)
    return DoctorConsultationOut(
        id=c.id,
        date=c.date,
        diagnosis_main=c.diagnosis_main,
        diagnosis_secondary=c.diagnosis_secondary,
        diagnosis_code=c.diagnosis_code,
        diagnosis_description=c.diagnosis_description,
        general_indications=c.general_indications,
        motivo_consulta=c.motivo_consulta,
        enfermedad_actual=c.enfermedad_actual,
        examen_fisico=c.examen_fisico,
        signos_vitales=c.signos_vitales,
        plan_tratamiento=c.plan_tratamiento,
        patient=patient_name,
        doctor=doctor_name,
    )


@router.post("", response_model=DoctorConsultationOut, status_code=status.HTTP_201_CREATED)
def create_consultation(
    payload: DoctorConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Crear una nueva consulta médica. El doctor es el usuario autenticado."""
    check_doctor_patient_access(payload.patient_id, db, current_user)
    patient = db.execute(select(Patient).where(Patient.id == payload.patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    consultation = Consultation(
        patient_id=payload.patient_id,
        doctor_id=current_user.id,
        diagnosis_main=payload.diagnosis_main,
        diagnosis_secondary=payload.diagnosis_secondary,
        diagnosis_code=payload.diagnosis_code,
        diagnosis_description=payload.diagnosis_description,
        general_indications=payload.general_indications,
        motivo_consulta=payload.motivo_consulta,
        enfermedad_actual=payload.enfermedad_actual,
        examen_fisico=payload.examen_fisico,
        signos_vitales=payload.signos_vitales,
        plan_tratamiento=payload.plan_tratamiento,
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    consultation = db.execute(
        select(Consultation)
        .where(Consultation.id == consultation.id)
        .options(selectinload(Consultation.patient))
    ).scalar_one()
    return _consultation_to_out(db, consultation)


@router.get("", response_model=list[DoctorConsultationOut])
def list_my_consultations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Listar solo las consultas del médico autenticado."""
    stmt = (
        select(Consultation)
        .where(Consultation.doctor_id == current_user.id)
        .options(selectinload(Consultation.patient))
        .order_by(Consultation.date.desc())
    )
    consultations = db.execute(stmt).scalars().all()
    return [_consultation_to_out(db, c) for c in consultations]


@router.get("/{consultation_id}", response_model=DoctorConsultationOut)
def get_consultation_detail(
    consultation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Obtener detalle de una consulta. Solo si pertenece al médico autenticado."""
    consultation = db.execute(
        select(Consultation)
        .where(Consultation.id == consultation_id)
        .options(selectinload(Consultation.patient))
    ).scalar_one_or_none()
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")
    if consultation.doctor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return _consultation_to_out(db, consultation)


@router.post("/{consultation_id}/medications", response_model=ConsultationMedicationOut, status_code=status.HTTP_201_CREATED)
def add_medication_to_consultation(
    consultation_id: UUID,
    payload: ConsultationMedicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Añadir un medicamento a la consulta."""
    consultation = db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    ).scalar_one_or_none()
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")
    if consultation.doctor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    drug = db.execute(select(Drug).where(Drug.id == payload.drug_id)).scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento no encontrado")
    cm = ConsultationMedication(
        consultation_id=consultation_id,
        drug_id=payload.drug_id,
        dose=payload.dose,
        route=payload.route,
        frequency=payload.frequency,
        duration=payload.duration,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    db.add(cm)
    db.commit()
    db.refresh(cm)
    return ConsultationMedicationOut(
        id=cm.id,
        consultation_id=str(cm.consultation_id),
        drug_id=cm.drug_id,
        dose=cm.dose,
        route=cm.route,
        frequency=cm.frequency,
        duration=cm.duration,
        quantity=cm.quantity,
        notes=cm.notes,
        drug_name=drug.name,
        drug_strength=drug.strength,
    )


@router.get("/{consultation_id}/medications", response_model=list[ConsultationMedicationOut])
def list_consultation_medications(
    consultation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Listar medicamentos de una consulta."""
    consultation = db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    ).scalar_one_or_none()
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")
    if consultation.doctor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    stmt = (
        select(ConsultationMedication, Drug)
        .join(Drug, ConsultationMedication.drug_id == Drug.id)
        .where(ConsultationMedication.consultation_id == consultation_id)
    )
    rows = db.execute(stmt).all()
    return [
        ConsultationMedicationOut(
            id=row[0].id,
            consultation_id=str(row[0].consultation_id),
            drug_id=row[0].drug_id,
            dose=row[0].dose,
            route=row[0].route,
            frequency=row[0].frequency,
            duration=row[0].duration,
            notes=row[0].notes,
            drug_name=row[1].name,
            drug_strength=row[1].strength,
        )
        for row in rows
    ]
