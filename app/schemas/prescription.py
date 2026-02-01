from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PrescriptionItemCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medication_name: str
    dose: str | None = None
    frequency: str | None = None
    duration: str | None = None
    route: str | None = None
    quantity: str | None = None
    notes: str | None = None


class PrescriptionCreate(BaseModel):
    consultation_id: UUID
    general_instructions: str | None = None
    items: list[PrescriptionItemCreate]


class PrescriptionOut(BaseModel):
    id: UUID
    consultation_id: UUID
    patient_id: UUID
    doctor_id: UUID
    general_instructions: str | None
    created_at: datetime
    items: list[PrescriptionItemCreate]

    model_config = ConfigDict(from_attributes=True)
