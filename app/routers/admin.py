from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_admin
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.consultation import Consultation
from app.models.doctor_patient import DoctorPatient
from app.models.doctor_profile import DoctorProfile
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.admin import DoctorCreate, DoctorStatusUpdate
from app.schemas.doctor_profile import AdminDoctorProfileUpdate
from app.schemas.subscription import SubscriptionOut, SubscriptionUpdate
from app.utils.audit import log_action

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_doctors = db.execute(select(func.count(User.id)).where(User.role == "doctor")).scalar() or 0
    active_doctors = (
        db.execute(
            select(func.count(Subscription.doctor_id)).where(Subscription.status == "active")
        ).scalar()
        or 0
    )
    suspended_doctors = (
        db.execute(
            select(func.count(Subscription.doctor_id)).where(Subscription.status == "suspended")
        ).scalar()
        or 0
    )
    total_recipes_this_month = (
        db.execute(
            select(func.count(Prescription.id)).where(
                Prescription.created_at >= month_start,
                Prescription.created_at <= now,
            )
        ).scalar()
        or 0
    )
    total_patients = db.execute(select(func.count(Patient.id))).scalar() or 0
    return {
        "total_doctors": total_doctors,
        "active_doctors": active_doctors,
        "suspended_doctors": suspended_doctors,
        "total_recipes_this_month": total_recipes_this_month,
        "total_patients": total_patients,
    }


@router.get("/audit")
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    doctor_id: UUID | None = Query(None),
    action: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    stmt = (
        select(AuditLog, User.email)
        .outerjoin(User, AuditLog.doctor_id == User.id)
        .order_by(AuditLog.timestamp.desc())
    )
    if doctor_id is not None:
        stmt = stmt.where(AuditLog.doctor_id == doctor_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if date_from is not None:
        stmt = stmt.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.timestamp <= date_to)
    result = db.execute(stmt).all()
    return [
        {
            "id": str(row[0].id),
            "doctor_id": str(row[0].doctor_id) if row[0].doctor_id else None,
            "doctor_email": row[1] if row[1] else None,
            "action": row[0].action,
            "entity_type": row[0].entity_type,
            "entity_id": row[0].entity_id,
            "timestamp": row[0].timestamp.isoformat() if row[0].timestamp else None,
            "ip_address": row[0].ip_address,
            "details": row[0].details,
        }
        for row in result
    ]


@router.post("/doctors")
def create_doctor(
    payload: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)
    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role="doctor",
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    db.add(DoctorProfile(user_id=user.id))
    db.add(
        Subscription(
            doctor_id=user.id,
            plan=payload.plan or "basic",
            status="active",
            start_date=now,
            current_period_start=now,
            current_period_end=period_end,
            max_recipes_per_cycle=50,
            max_patients=200,
        )
    )
    log_action(
        db,
        current_user.id,
        "ADMIN_CREATE_DOCTOR",
        "user",
        str(user.id),
        details={"plan": payload.plan or "basic"},
    )
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "email": user.email, "role": user.role}


@router.get("/doctors")
def list_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    subq = (
        select(func.count(Prescription.id))
        .where(Prescription.doctor_id == User.id)
        .where(
            Prescription.created_at >= Subscription.current_period_start,
            Prescription.created_at <= Subscription.current_period_end,
        )
        .correlate(User, Subscription)
        .scalar_subquery()
    )
    stmt = (
        select(User, Subscription, DoctorProfile, subq.label("recipes_in_period"))
        .outerjoin(Subscription, Subscription.doctor_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .where(User.role == "doctor")
    )
    result = db.execute(stmt).all()
    return [
        {
            "id": str(row[0].id),
            "email": row[0].email,
            "role": row[0].role,
            "must_change_password": getattr(row[0], "must_change_password", False),
            "subscription_plan": row[1].plan if row[1] else None,
            "subscription_status": row[1].status if row[1] else None,
            "current_period_end": row[1].current_period_end.isoformat() if row[1] and row[1].current_period_end else None,
            "recipes_in_period": row[3] if row[3] is not None else 0,
            "nombres": row[2].nombres if row[2] else None,
            "apellidos": row[2].apellidos if row[2] else None,
            "especialidad": row[2].specialty if row[2] else None,
        }
        for row in result
    ]


def _get_or_create_doctor_profile(db: Session, doctor_id: UUID) -> DoctorProfile:
    profile = db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == doctor_id)
    ).scalars().one_or_none()
    if profile is None:
        profile = DoctorProfile(user_id=doctor_id)
        db.add(profile)
        db.flush()
    return profile


@router.get("/doctors/{doctor_id}/profile")
def get_doctor_profile(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.execute(select(User).where(User.id == doctor_id)).scalars().one_or_none()
    if not user or user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    profile = db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == doctor_id)
    ).scalars().one_or_none()
    base = {"email": user.email}
    if not profile:
        return base
    base.update({
        "full_name": profile.full_name,
        "specialty": profile.specialty,
        "phone": profile.phone,
        "address": profile.address,
        "first_name": profile.nombres,
        "last_name": profile.apellidos,
        "date_of_birth": profile.fecha_nacimiento.isoformat() if profile.fecha_nacimiento else None,
        "gender": profile.sexo,
        "province": profile.provincia,
        "city": profile.ciudad,
        "country": profile.pais,
        "professional_reg_number": profile.senescyt_reg or profile.medical_license,
    })
    return base


@router.put("/doctors/{doctor_id}/profile")
def update_doctor_profile(
    doctor_id: UUID,
    payload: AdminDoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.execute(select(User).where(User.id == doctor_id)).scalars().one_or_none()
    if not user or user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    profile = _get_or_create_doctor_profile(db, doctor_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("first_name") is not None:
        profile.nombres = data["first_name"] or None
    if data.get("last_name") is not None:
        profile.apellidos = data["last_name"] or None
    if data.get("date_of_birth") is not None:
        val = data["date_of_birth"]
        if isinstance(val, str) and val.strip():
            from datetime import date
            try:
                profile.fecha_nacimiento = date.fromisoformat(val)
            except (ValueError, TypeError):
                profile.fecha_nacimiento = None
        else:
            profile.fecha_nacimiento = None
    if data.get("gender") is not None:
        profile.sexo = data["gender"] or None
    if data.get("country") is not None:
        profile.pais = data["country"] or None
    if data.get("province") is not None:
        profile.provincia = data["province"] or None
    if data.get("city") is not None:
        profile.ciudad = data["city"] or None
    if data.get("specialty") is not None:
        profile.specialty = data["specialty"] or None
    if data.get("full_name") is not None:
        profile.full_name = data["full_name"] or None
    if data.get("phone") is not None:
        profile.phone = data["phone"] or None
    if data.get("address") is not None:
        profile.address = data["address"] or None
    if data.get("professional_reg_number") is not None:
        profile.senescyt_reg = data["professional_reg_number"] or None
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {
        "full_name": profile.full_name,
        "specialty": profile.specialty,
        "phone": profile.phone,
        "address": profile.address,
        "first_name": profile.nombres,
        "last_name": profile.apellidos,
        "date_of_birth": profile.fecha_nacimiento.isoformat() if profile.fecha_nacimiento else None,
        "gender": profile.sexo,
        "province": profile.provincia,
        "city": profile.ciudad,
        "country": profile.pais,
        "professional_reg_number": profile.senescyt_reg or profile.medical_license,
    }


@router.put("/subscriptions/{doctor_id}", response_model=SubscriptionOut)
def update_subscription(
    doctor_id: UUID,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    subscription = db.execute(
        select(Subscription).where(Subscription.doctor_id == doctor_id)
    ).scalars().one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(subscription, key, value)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.put("/doctors/{doctor_id}/status")
def update_doctor_status(
    doctor_id: UUID,
    payload: DoctorStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    subscription = db.execute(
        select(Subscription).where(Subscription.doctor_id == doctor_id)
    ).scalars().one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    subscription.status = payload.status
    db.add(subscription)
    db.commit()
    return {"message": "Status updated", "status": payload.status}


@router.get("/doctors/{doctor_id}/usage")
def get_doctor_usage(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    subscription = db.execute(
        select(Subscription).where(Subscription.doctor_id == doctor_id)
    ).scalars().one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    recipes_count = db.execute(
        select(func.count(Prescription.id)).where(
            Prescription.doctor_id == doctor_id,
            Prescription.created_at >= subscription.current_period_start,
            Prescription.created_at <= subscription.current_period_end,
        )
    ).scalar() or 0
    patients_count = db.execute(
        select(func.count(DoctorPatient.id)).where(DoctorPatient.doctor_id == doctor_id)
    ).scalar() or 0
    return {
        "recetas_en_periodo_actual": recipes_count,
        "limite_recetas": subscription.max_recipes_per_cycle,
        "pacientes_registrados": patients_count,
        "limite_pacientes": subscription.max_patients,
    }


@router.get("/doctors/{doctor_id}/analytics")
def get_doctor_analytics(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Métricas agregadas por médico. Solo lectura, sin datos de pacientes."""
    total_consultations = (
        db.execute(select(func.count()).select_from(Consultation).where(Consultation.doctor_id == doctor_id)).scalar()
        or 0
    )
    total_prescriptions = (
        db.execute(select(func.count()).select_from(Prescription).where(Prescription.doctor_id == doctor_id)).scalar()
        or 0
    )
    unique_patients = (
        db.execute(
            select(func.count(func.distinct(Consultation.patient_id))).where(Consultation.doctor_id == doctor_id)
        ).scalar()
        or 0
    )
    top_diagnoses = (
        db.execute(
            select(Consultation.diagnosis, func.count().label("count"))
            .where(Consultation.doctor_id == doctor_id)
            .where(Consultation.diagnosis.isnot(None))
            .group_by(Consultation.diagnosis)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    top_medications = (
        db.execute(
            select(PrescriptionItem.medication_name, func.count().label("count"))
            .join(Prescription, Prescription.id == PrescriptionItem.prescription_id)
            .where(Prescription.doctor_id == doctor_id)
            .group_by(PrescriptionItem.medication_name)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    meds_per_prescription_subq = (
        select(PrescriptionItem.prescription_id, func.count().label("count"))
        .join(Prescription, Prescription.id == PrescriptionItem.prescription_id)
        .where(Prescription.doctor_id == doctor_id)
        .group_by(PrescriptionItem.prescription_id)
    ).subquery()
    avg_meds = (
        db.execute(select(func.avg(meds_per_prescription_subq.c.count)).select_from(meds_per_prescription_subq))
        .scalar()
    )
    return {
        "total_consultations": total_consultations,
        "total_prescriptions": total_prescriptions,
        "unique_patients": unique_patients,
        "top_diagnoses": [{"diagnosis": d, "count": c} for d, c in top_diagnoses],
        "top_medications": [{"name": m, "count": c} for m, c in top_medications],
        "avg_medications_per_prescription": float(avg_meds or 0),
    }


@router.post("/doctors/{doctor_id}/reset-password")
@router.put("/doctors/{doctor_id}/reset-password")
def admin_reset_doctor_password(
    doctor_id: UUID,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    new_password = payload.get("new_password")
    if not new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="new_password required")
    if len(new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    doctor = db.execute(
        select(User).where(User.id == doctor_id, User.role == "doctor")
    ).scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    doctor.password_hash = get_password_hash(new_password)
    doctor.must_change_password = True
    db.add(doctor)
    db.commit()

    log_action(
        db,
        current_user.id,
        "ADMIN_RESET_PASSWORD",
        "user",
        str(doctor_id),
        details={"force_change": True},
    )
    return {"message": "Password updated"}


@router.put("/doctors/{doctor_id}/force-password-change")
def admin_force_password_change(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    doctor = db.execute(
        select(User).where(User.id == doctor_id, User.role == "doctor")
    ).scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    doctor.must_change_password = True
    db.add(doctor)
    db.commit()
    log_action(db, current_user.id, "ADMIN_FORCE_PASSWORD_CHANGE", "user", str(doctor_id))
    return {"message": "Password change enforced"}


@router.put("/doctors/{doctor_id}/account-status")
def admin_update_doctor_account_status(
    doctor_id: UUID,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    status_val = payload.get("status")
    if status_val not in ("active", "suspended"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    doctor = db.execute(
        select(User).where(User.id == doctor_id, User.role == "doctor")
    ).scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    subscription = db.execute(
        select(Subscription).where(Subscription.doctor_id == doctor_id)
    ).scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    if status_val == "suspended":
        doctor.is_active = False
        subscription.status = "suspended"
    else:
        doctor.is_active = True
        subscription.status = "active"

    db.add(doctor)
    db.add(subscription)
    db.commit()

    log_action(db, current_user.id, "ADMIN_ACCOUNT_STATUS_CHANGE", "user", str(doctor_id))
    return {"message": "Account status updated", "status": status_val}


@router.delete("/doctors/{doctor_id}/profile")
def admin_delete_doctor_profile(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    profile = db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == doctor_id)
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    db.delete(profile)
    db.commit()

    log_action(db, current_user.id, "ADMIN_DELETE_DOCTOR_PROFILE", "doctor_profile", str(doctor_id))
    return {"message": "Doctor profile deleted"}
