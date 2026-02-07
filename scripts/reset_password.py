import os
import sys


def _ensure_import_path() -> None:
    """Allow running as: python backend/scripts/reset_password.py"""
    here = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(here, ".."))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


_ensure_import_path()

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402


EMAIL = "davidguzman.med@gmail.com"
NEW_PASSWORD = "Admin123!"


def main() -> int:
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == EMAIL)).scalar_one_or_none()
        if not user:
            raise SystemExit(f"User not found: {EMAIL}")

        user.password_hash = get_password_hash(NEW_PASSWORD)
        db.add(user)
        db.commit()

        print(f"User found: {EMAIL}")
        print("Password reset successful")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
