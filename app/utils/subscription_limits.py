from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.prescription import Prescription
from app.models.doctor_patient import DoctorPatient
from app.models.patient import Patient
from app.models.subscription import Subscription


def check_recipe_limit(db: Session, doctor_id: UUID) -> None:
    """
    Verifica si el médico puede crear una receta
    según su plan y ciclo actual.
    """
    subscription = db.execute(
        select(Subscription).where(Subscription.doctor_id == doctor_id)
    ).scalars().one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription",
        )

    if subscription.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription",
        )

    if subscription.max_recipes_per_cycle is None:
        return

    count_stmt = (
        select(func.count(Prescription.id)).where(
            Prescription.doctor_id == doctor_id,
            Prescription.created_at >= subscription.current_period_start,
            Prescription.created_at <= subscription.current_period_end,
        )
    )
    count = db.execute(count_stmt).scalar() or 0

    if count >= subscription.max_recipes_per_cycle:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plan limit reached",
        )


def check_patient_limit(db: Session, doctor_id: UUID) -> None:
    """
    Verifica si el médico puede crear un paciente nuevo
    según su plan y ciclo actual.
    """
    subscription = db.execute(
        select(Subscription).where(Subscription.doctor_id == doctor_id)
    ).scalars().one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription",
        )

    if subscription.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription",
        )

    plan = (subscription.plan or "").strip().lower()
    if plan != "emprendedor":
        return

    limit = subscription.max_patients if subscription.max_patients is not None else 250

    count_stmt = (
        select(func.count(func.distinct(Patient.id))).where(
            or_(
                Patient.doctor_id == doctor_id,
                Patient.id.in_(
                    select(DoctorPatient.patient_id).where(
                        DoctorPatient.doctor_id == doctor_id
                    )
                ),
            )
        )
    )
    count = db.execute(count_stmt).scalar() or 0

    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Has alcanzado el límite de pacientes del plan Emprendedor ({limit}). "
                "Actualiza a Profesional para seguir agregando pacientes."
            ),
        )
