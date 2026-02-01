from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import check_doctor_patient_access, require_doctor, verify_consultation_access
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.user import User
from app.models.vital_signs import VitalSigns
from app.schemas.consultation import ConsultationCreate, ConsultationOut
from app.schemas.vital_signs import VitalSignsOut
from app.utils.audit import log_action

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.post("", response_model=ConsultationOut, status_code=status.HTTP_201_CREATED)
def create_consultation(
    request: Request,
    payload: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    check_doctor_patient_access(payload.patient_id, db, current_user)
    patient = db.execute(select(Patient).where(Patient.id == payload.patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    consultation = Consultation(
        patient_id=payload.patient_id,
        doctor_id=current_user.id,
        diagnosis=payload.diagnosis,
        clinical_notes=payload.clinical_notes,
        weight=payload.weight,
        blood_pressure=payload.blood_pressure,
        heart_rate=payload.heart_rate,
        oxygen_saturation=payload.oxygen_saturation,
    )
    db.add(consultation)
    db.flush()
    if payload.vital_signs:
        vs = payload.vital_signs
        vital = VitalSigns(
            consultation_id=consultation.id,
            blood_pressure_systolic=vs.blood_pressure_systolic,
            blood_pressure_diastolic=vs.blood_pressure_diastolic,
            heart_rate=vs.heart_rate,
            respiratory_rate=vs.respiratory_rate,
            temperature=vs.temperature,
            oxygen_saturation=vs.oxygen_saturation,
            weight_kg=vs.weight_kg,
            height_cm=vs.height_cm,
            bmi=vs.bmi,
            notes=vs.notes,
        )
        db.add(vital)
    log_action(
        db,
        doctor_id=current_user.id,
        action="CREATE_CONSULTATION",
        entity_type="consultation",
        entity_id=str(consultation.id),
        details={"patient_id": str(payload.patient_id)},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/{consultation_id}/vitals", response_model=VitalSignsOut | None)
def get_consultation_vitals(
    consultation_id: UUID,
    db: Session = Depends(get_db),
    consultation: Consultation = Depends(verify_consultation_access),
):
    vital = db.execute(
        select(VitalSigns).where(VitalSigns.consultation_id == consultation.id)
    ).scalars().one_or_none()
    return vital


@router.get("/{consultation_id}", response_model=ConsultationOut)
def get_consultation(
    consultation_id: UUID,
    consultation: Consultation = Depends(verify_consultation_access),
):
    return consultation
