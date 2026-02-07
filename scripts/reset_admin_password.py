import os
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

TARGET_EMAIL = os.getenv("RESET_EMAIL", "davidguzman.med@gmail.com")
TEMP_PASSWORD = os.getenv("RESET_PASSWORD", "Admin123!")


def main() -> None:
    db = SessionLocal()
    try:
        # Buscar usuario existente
        user = db.execute(
            select(User).where(User.email == TARGET_EMAIL)
        ).scalar_one_or_none()

        if not user:
            print("❌ User not found")
            print(f"Email: {TARGET_EMAIL}")
            return

        print("✅ User found")
        print(f"Email: {user.email}")

        user.password_hash = get_password_hash(TEMP_PASSWORD)
        user.must_change_password = False
        user.is_active = True
        db.add(user)
        db.commit()

        print("✅ Email reset")
        print("Password reset successful")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
