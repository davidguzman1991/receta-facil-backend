import os
import sys


def _ensure_import_path() -> None:
    """Allow running as: python backend/scripts/reset_password_admin.py"""
    here = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(here, ".."))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


_ensure_import_path()

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402


TARGET_EMAIL = os.getenv("RESET_EMAIL", "davidguzman.med@gmail.com")
NEW_PASSWORD = os.getenv("RESET_PASSWORD", "Admin123!")


def main() -> int:
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == TARGET_EMAIL)).scalar_one_or_none()
        if not user:
            print(f"User not found: {TARGET_EMAIL}")
            return 2

        user.password_hash = get_password_hash(NEW_PASSWORD)
        db.add(user)
        db.commit()

        print(f"User found: {TARGET_EMAIL}")
        print("Password reset successful")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
