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
from app.core.security import get_password_hash, verify_password  # noqa: E402
from app.models.user import User  # noqa: E402


TARGET_EMAIL = os.getenv("RESET_EMAIL", "davidguzman.med@gmail.com")
NEW_PASSWORD = os.getenv("RESET_PASSWORD", "Admin123!")


def main() -> int:
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == TARGET_EMAIL)).scalar_one_or_none()
        if not user:
            raise RuntimeError(f"User not found: {TARGET_EMAIL}")

        new_hash = get_password_hash(NEW_PASSWORD)
        user.password_hash = new_hash
        db.add(user)
        db.commit()
        db.refresh(user)

        if not verify_password(NEW_PASSWORD, user.password_hash):
            raise RuntimeError(
                f"CASCADE FAIL → Hash verification failed for {TARGET_EMAIL}. "
                "Password not updated safely."
            )

        print(f"CASCADE OK → Password reset & verified for {TARGET_EMAIL}")
        return 0
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
