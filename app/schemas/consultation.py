from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.vital_signs import VitalSignsCreate


class ConsultationCreate(BaseModel):
    patient_id: UUID
    diagnosis: str | None = None
    clinical_notes: str | None = None
    weight: float | None = None
    blood_pressure: str | None = None
    heart_rate: int | None = None
    oxygen_saturation: int | None = None
    vital_signs: VitalSignsCreate | None = None
    motivo_consulta: str | None = None
    enfermedad_actual: str | None = None
    examen_fisico: str | None = None
    signos_vitales: dict | None = None
    plan_tratamiento: str | None = None


class ConsultationOut(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    date: datetime
    diagnosis: str | None
    clinical_notes: str | None
    weight: float | None
    blood_pressure: str | None
    heart_rate: int | None
    oxygen_saturation: int | None
    diagnosis_code: str | None = None
    diagnosis_description: str | None = None
    motivo_consulta: str | None = None
    enfermedad_actual: str | None = None
    examen_fisico: str | None = None
    signos_vitales: dict | None = None
    plan_tratamiento: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Esquemas para el portal médico (Nueva Consulta Médica) ---


class DoctorConsultationCreate(BaseModel):
    """Payload para crear una consulta desde el portal del médico."""
    patient_id: UUID
    diagnosis_main: str
    diagnosis_secondary: str | None = None
    diagnosis_code: str | None = None
    diagnosis_description: str | None = None
    general_indications: str | None = None
    motivo_consulta: str | None = None
    enfermedad_actual: str | None = None
    examen_fisico: str | None = None
    signos_vitales: dict | None = None
    plan_tratamiento: str | None = None


class DoctorConsultationOut(BaseModel):
    """Respuesta de consulta con nombres de paciente y médico."""
    id: UUID
    date: datetime
    diagnosis_main: str | None
    diagnosis_secondary: str | None
    diagnosis_code: str | None = None
    diagnosis_description: str | None = None
    general_indications: str | None
    motivo_consulta: str | None = None
    enfermedad_actual: str | None = None
    examen_fisico: str | None = None
    signos_vitales: dict | None = None
    plan_tratamiento: str | None = None
    patient: str  # nombre completo
    doctor: str   # nombre completo

    model_config = ConfigDict(from_attributes=True)
