from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_doctor
from app.models.doctor_patient import DoctorPatient
from app.models.patient import Patient
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.patient import PatientOut
from app.schemas.subscription import SubscriptionOut

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/subscription", response_model=SubscriptionOut | None)
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    subscription = db.execute(
        select(Subscription).where(Subscription.doctor_id == current_user.id)
    ).scalars().one_or_none()
    return subscription


@router.get("/patients", response_model=list[PatientOut])
def list_my_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    stmt = (
        select(Patient)
        .where(
            or_(
                Patient.doctor_id == current_user.id,
                Patient.id.in_(
                    select(DoctorPatient.patient_id).where(
                        DoctorPatient.doctor_id == current_user.id
                    )
                ),
            )
        )
        .distinct()
    )
    result = db.execute(stmt).scalars().all()
    return list(result)
