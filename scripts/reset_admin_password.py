from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

# 🔥 IMPORTAR TODOS LOS MODELOS PARA QUE SQLALCHEMY REGISTRE RELACIONES
from app.models import user
from app.models import patient
from app.models import doctor_profile
from app.models import consultation
from app.models import consultation_medication
from app.models import icd10
from app.models import doctor_patient
from app.models import drug
from app.models import prescription
from app.models import prescription_item
from app.models import subscription
from app.models import vital_signs
from app.models import audit_log

ADMIN_EMAIL = "anovamedicalresearch@gmail.com"
ADMIN_PASSWORD = "admin123"


def main() -> None:
    db = SessionLocal()
    try:
        # Buscar usuario existente
        user = db.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        ).scalar_one_or_none()

        if user:
            # Usuario existe, actualizar password
            user.password_hash = get_password_hash(ADMIN_PASSWORD)
            user.must_change_password = False
            user.is_active = True
            db.commit()
            print(f"✅ Usuario actualizado.")
        else:
            # Usuario no existe, crear nuevo
            new_user = User(
                email=ADMIN_EMAIL,
                password_hash=get_password_hash(ADMIN_PASSWORD),
                role="doctor",
                is_active=True,
                must_change_password=False,
            )
            db.add(new_user)
            db.commit()
            print(f"✅ Usuario creado.")

        print(f"📧 Email: {ADMIN_EMAIL}")
        print(f"🔑 Password: {ADMIN_PASSWORD}")
        print(f"\n✅ Usuario admin listo. Email: {ADMIN_EMAIL} | Password: {ADMIN_PASSWORD}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
