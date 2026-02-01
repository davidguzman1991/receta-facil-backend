from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.core.deps import require_doctor, verify_prescription_access
from app.models.consultation import Consultation
from app.models.doctor_profile import DoctorProfile
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.user import User
from app.schemas.prescription import PrescriptionCreate, PrescriptionOut
from app.services.email_service import send_prescription_email
from app.services.pdf_prescription import generate_prescription_pdf
from app.utils.audit import log_action
from app.utils.subscription_limits import check_recipe_limit

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


async def _send_prescription_email_task(
    prescription_id: UUID,
    doctor_id: UUID,
    ip_address: str | None,
) -> None:
    """Tarea en segundo plano: genera PDF, envía email al paciente y registra auditoría."""
    db = SessionLocal()
    try:
        prescription = db.execute(
            select(Prescription)
            .options(
                selectinload(Prescription.items),
                joinedload(Prescription.patient).joinedload(Patient.user),
                joinedload(Prescription.doctor),
            )
            .where(Prescription.id == prescription_id)
        ).scalar_one_or_none()
        if not prescription:
            return

        patient = prescription.patient
        doctor = prescription.doctor
        doctor_profile = db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == doctor.id)
        ).scalar_one_or_none()

        smtp_configured = all([
            settings.SMTP_HOST,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.SMTP_FROM,
        ])
        if not smtp_configured:
            log_action(
                db,
                doctor_id=doctor_id,
                action="EMAIL_NOT_CONFIGURED",
                entity_type="prescription",
                entity_id=str(prescription_id),
                details=None,
                ip_address=ip_address,
            )
            db.commit()
            return

        to_email = None
        if patient.user:
            to_email = getattr(patient.user, "email", None)

        if not to_email:
            log_action(
                db,
                doctor_id=doctor_id,
                action="EMAIL_PRESCRIPTION_FAILED",
                entity_type="prescription",
                entity_id=str(prescription_id),
                details={"reason": "no patient email"},
                ip_address=ip_address,
            )
            db.commit()
            return

        patient_name = f"{patient.first_name} {patient.last_name}".strip() or "Paciente"
        buffer = generate_prescription_pdf(
            prescription, doctor, patient, doctor_profile=doctor_profile
        )
        pdf_bytes = buffer.getvalue()
        filename = "receta.pdf"

        success = await send_prescription_email(
            to_email=to_email,
            patient_name=patient_name,
            pdf_bytes=pdf_bytes,
            filename=filename,
        )

        if success:
            log_action(
                db,
                doctor_id=doctor_id,
                action="EMAIL_PRESCRIPTION_SENT",
                entity_type="prescription",
                entity_id=str(prescription_id),
                details=None,
                ip_address=ip_address,
            )
        else:
            log_action(
                db,
                doctor_id=doctor_id,
                action="EMAIL_PRESCRIPTION_FAILED",
                entity_type="prescription",
                entity_id=str(prescription_id),
                details={"reason": "send failed"},
                ip_address=ip_address,
            )
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


@router.post("", response_model=PrescriptionOut, status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: PrescriptionCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    consultation = db.execute(
        select(Consultation).where(Consultation.id == payload.consultation_id)
    ).scalar_one_or_none()
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    if consultation.doctor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your consultation")

    check_recipe_limit(db, current_user.id)

    prescription = Prescription(
        consultation_id=payload.consultation_id,
        patient_id=consultation.patient_id,
        doctor_id=current_user.id,
        general_instructions=payload.general_instructions,
    )
    db.add(prescription)
    db.flush()

    for item in payload.items:
        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medication_name=item.medication_name,
                dose=item.dose,
                frequency=item.frequency,
                duration=item.duration,
                route=item.route,
                quantity=item.quantity,
                notes=item.notes,
            )
        )
    log_action(
        db,
        doctor_id=current_user.id,
        action="CREATE_PRESCRIPTION",
        entity_type="prescription",
        entity_id=str(prescription.id),
        details={"consultation_id": str(payload.consultation_id)},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(prescription)

    background_tasks.add_task(
        _send_prescription_email_task,
        prescription.id,
        current_user.id,
        request.client.host if request.client else None,
    )
    return prescription


@router.get("/{prescription_id}/pdf")
def get_prescription_pdf(
    db: Session = Depends(get_db),
    prescription: Prescription = Depends(verify_prescription_access),
):
    doctor = prescription.doctor
    patient = prescription.patient
    doctor_profile = db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == doctor.id)
    ).scalar_one_or_none()
    buffer = generate_prescription_pdf(
        prescription, doctor, patient, doctor_profile=doctor_profile
    )
    return StreamingResponse(
        buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=receta.pdf"},
    )


@router.get("/{prescription_id}", response_model=PrescriptionOut)
def get_prescription(
    prescription_id: UUID,
    prescription: Prescription = Depends(verify_prescription_access),
):
    return prescription
