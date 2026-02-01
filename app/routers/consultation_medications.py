"""Eliminar medicamento de una consulta."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_doctor
from app.models.consultation import Consultation
from app.models.consultation_medication import ConsultationMedication
from app.models.user import User

router = APIRouter(prefix="/consultation-medications", tags=["consultation-medications"])


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consultation_medication(
    medication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor),
):
    """Eliminar un medicamento de la consulta. Solo si la consulta es del médico autenticado."""
    cm = db.execute(
        select(ConsultationMedication).where(ConsultationMedication.id == medication_id)
    ).scalar_one_or_none()
    if not cm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento de consulta no encontrado")
    consultation = db.execute(
        select(Consultation).where(Consultation.id == cm.consultation_id)
    ).scalar_one_or_none()
    if not consultation or consultation.doctor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento de consulta no encontrado")
    db.delete(cm)
    db.commit()
    return None
