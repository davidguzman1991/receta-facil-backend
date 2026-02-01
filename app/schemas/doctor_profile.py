from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DoctorProfileUpdate(BaseModel):
    full_name: str | None = None
    specialty: str | None = None
    senescyt_reg: str | None = None
    medical_license: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    signature_image: str | None = None
    stamp_image: str | None = None
    signature_url: str | None = None
    stamp_url: str | None = None
    nombres: str | None = None
    apellidos: str | None = None
    fecha_nacimiento: date | None = None
    sexo: str | None = None
    pais: str | None = None
    provincia: str | None = None
    ciudad: str | None = None


class AdminDoctorProfileUpdate(BaseModel):
    """Payload del frontend admin: first_name, last_name, etc. Se mapean a nombres, apellidos en el modelo."""
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: str | None = None  # ISO date string from frontend
    gender: str | None = None
    specialty: str | None = None
    subspecialty: str | None = None
    professional_reg_number: str | None = None
    institution: str | None = None
    province: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    address: str | None = None


class DoctorProfileOut(DoctorProfileUpdate):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)
