from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: Literal["admin", "doctor", "patient"]
    is_active: bool
    must_change_password: bool


class LoginResponse(BaseModel):
    """Respuesta unificada de login: un solo login con rol para redirección."""
    access_token: str
    token_type: str = "bearer"
    role: Literal["admin", "doctor", "patient"]
    must_change_password: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str
    confirm_password: str


class ActivateAccountRequest(BaseModel):
    """Token de activación y nueva contraseña para cuenta de paciente."""
    token: str
    new_password: str
