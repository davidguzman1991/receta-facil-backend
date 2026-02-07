from datetime import datetime, timedelta
import logging
import os
import secrets
from urllib.parse import urlparse

from uuid import UUID

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import (
    ActivateAccountRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    UserOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_TTL = timedelta(minutes=30)
RESET_TOKENS: dict[str, dict[str, str | datetime]] = {}


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked = (name[:1] + "*") if name else "*"
    else:
        masked = name[:1] + ("*" * (len(name) - 2)) + name[-1:]
    return f"{masked}@{domain}"


def _db_host() -> str:
    url = settings.database_url
    try:
        parsed = urlparse(url)
        if parsed.scheme.startswith("sqlite"):
            return "sqlite"
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        return f"{host}{port}" or parsed.scheme
    except Exception:
        return "unknown"


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    # Nota: este endpoint usa JSON { email, password } (no OAuth2 form).
    try:
        # Diagnóstico temporal: email (enmascarado) + host de DB activo.
        logger.info(
            "Login attempt email=%s db_host=%s",
            _mask_email(payload.email),
            _db_host(),
        )
        logger.info(
            "Login payload received email=%s password_len=%s",
            _mask_email(payload.email),
            len(payload.password) if payload.password else 0,
        )
        user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        if not user:
            logger.warning("Login failed: user not found email=%s", _mask_email(payload.email))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        try:
            logger.info("Login validating password email=%s", _mask_email(payload.email))
            if not verify_password(payload.password, user.password_hash):
                logger.warning("Login failed: bad password email=%s", _mask_email(payload.email))
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        except Exception:
            logger.exception("Login failed: password verification error email=%s", _mask_email(payload.email))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        if not user.is_active:
            logger.warning("Login failed: inactive user email=%s", _mask_email(payload.email))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

        token = create_access_token(sub=str(user.id), role=user.role)
        response.set_cookie(
            key="rf_access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            role=user.role,
            must_change_password=getattr(user, "must_change_password", False),
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Login failed: database error")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc
    except Exception as exc:
        logger.exception("Login failed: unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from exc


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="rf_access_token", path="/")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")
    if payload.current_password:
        if not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password")
    else:
        # Permitir cambio sin contraseña actual solo cuando el usuario está obligado a cambiarla
        if not getattr(current_user, "must_change_password", False):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current_password required")

    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()
    return {"message": "Password updated"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user:
        token = secrets.token_urlsafe(32)
        RESET_TOKENS[token] = {
            "user_id": str(user.id),
            "expires_at": datetime.utcnow() + RESET_TOKEN_TTL,
        }
        if settings.APP_ENV.lower() != "production":
            return {"message": "Reset token generated", "token": token}

    return {"message": "If the email exists, a reset token has been sent"}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_data = RESET_TOKENS.get(payload.token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    expires_at = token_data.get("expires_at")
    if not isinstance(expires_at, datetime) or expires_at < datetime.utcnow():
        RESET_TOKENS.pop(payload.token, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user_id = token_data.get("user_id")
    if not isinstance(user_id, str):
        RESET_TOKENS.pop(payload.token, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        RESET_TOKENS.pop(payload.token, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = db.execute(select(User).where(User.id == user_uuid)).scalar_one_or_none()
    if not user:
        RESET_TOKENS.pop(payload.token, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user.password_hash = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    RESET_TOKENS.pop(payload.token, None)
    return {"message": "Password reset successful"}


@router.post("/admin-reset-all-users")
def admin_reset_all_users(x_admin_reset_token: str | None = Header(default=None)):
    enabled = os.getenv("ADMIN_RESET_ALL_USERS_ENABLED", "false").strip().lower() == "true"
    expected_token = os.getenv("ADMIN_RESET_ALL_USERS_TOKEN", "").strip()
    if not enabled or not expected_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not x_admin_reset_token or x_admin_reset_token.strip() != expected_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    email = os.getenv("RESET_EMAIL", "davidguzman.med@gmail.com").strip()
    password = os.getenv("RESET_PASSWORD", "Admin123!")

    db = SessionLocal()
    try:
        db.execute(delete(User))
        db.commit()

        admin_user = User(
            email=email,
            password_hash=get_password_hash(password),
            role="admin",
            is_active=True,
            must_change_password=False,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        return {"message": "ok", "email": admin_user.email, "role": admin_user.role}
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


def _get_user_by_activation_token(db: Session, token: str) -> User | None:
    if not token or not token.strip():
        return None
    return db.execute(
        select(User).where(User.activation_token == token.strip())
    ).scalar_one_or_none()


def _is_activation_token_valid(user: User | None) -> bool:
    if not user:
        return False
    if not user.activation_token or not user.activation_token_expires_at:
        return False
    now = datetime.now(timezone.utc)
    expires = user.activation_token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > now


@router.get("/activate-account")
def validate_activation_token(
    token: str = Query(..., alias="token"),
    db: Session = Depends(get_db),
):
    """
    Valida si el token de activación es válido y no ha expirado.
    No revela si el email existe o no; respuestas genéricas.
    """
    user = _get_user_by_activation_token(db, token)
    if not _is_activation_token_valid(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    return {"valid": True}


@router.post("/activate-account")
def activate_account(
    payload: ActivateAccountRequest,
    db: Session = Depends(get_db),
):
    """
    Activa la cuenta del paciente: establece contraseña, activa usuario y limpia token.
    """
    user = _get_user_by_activation_token(db, payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    if not _is_activation_token_valid(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    user.password_hash = get_password_hash(payload.new_password)
    user.is_active = True
    user.activation_token = None
    user.activation_token_expires_at = None
    db.add(user)
    db.commit()
    return {"message": "Account activated"}
