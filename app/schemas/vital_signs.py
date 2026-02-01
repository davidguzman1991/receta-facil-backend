from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VitalSignsCreate(BaseModel):
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    temperature: float | None = None
    oxygen_saturation: int | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    bmi: float | None = None
    notes: str | None = None


class VitalSignsOut(VitalSignsCreate):
    id: UUID
    consultation_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
