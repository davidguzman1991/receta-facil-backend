from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    phone: str | None = None


class DoctorPatientCreate(BaseModel):
    """Payload para que el médico cree un paciente (portal doctor)."""
    first_name: str
    last_name: str
    dni: str | None = None
    birth_date: date | None = None  # se mapea a date_of_birth
    sex: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    province: str | None = None
    city: str | None = None
    anamnesis: str | None = None
    personal_history: str | None = None
    allergic_history: str | None = None
    gyneco_history: str | None = None
    surgical_history: str | None = None


class PatientHistoryUpdate(BaseModel):
    anamnesis: str | None = None
    personal_history: str | None = None
    allergic_history: str | None = None
    gyneco_history: str | None = None
    surgical_history: str | None = None


class AssignDoctor(BaseModel):
    doctor_id: UUID


class PatientInvite(BaseModel):
    """Payload para invitar a un paciente a activar su cuenta."""
    email: str  # EmailStr en producción; str para validación mínima


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    first_name: str
    last_name: str
    email: str | None = None
    date_of_birth: date | None
    phone: str | None
    dni: str | None = None
    sex: str | None = None
    address: str | None = None
    province: str | None = None
    city: str | None = None
    anamnesis: str | None = None
    personal_history: str | None = None
    allergic_history: str | None = None
    gyneco_history: str | None = None
    surgical_history: str | None = None
    doctor_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ConsultationSummaryOut(BaseModel):
    """Resumen de consulta para historial del paciente."""
    id: UUID
    date: datetime
    diagnosis_main: str | None
    diagnosis_secondary: str | None

    model_config = ConfigDict(from_attributes=True)


class PatientDetailOut(PatientOut):
    """Paciente con historial de consultas."""
    consultations: list[ConsultationSummaryOut] = []
