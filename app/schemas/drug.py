from pydantic import BaseModel, ConfigDict


class DrugCreate(BaseModel):
    name: str
    presentation: str | None = None
    strength: str | None = None


class DrugOut(BaseModel):
    id: int
    name: str
    presentation: str | None
    strength: str | None

    model_config = ConfigDict(from_attributes=True)


class ConsultationMedicationCreate(BaseModel):
    drug_id: int
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None
    quantity: str | None = None
    notes: str | None = None


class ConsultationMedicationOut(BaseModel):
    id: int
    consultation_id: str
    drug_id: int
    dose: str | None
    route: str | None
    frequency: str | None
    duration: str | None
    quantity: str | None
    notes: str | None
    drug_name: str | None = None
    drug_strength: str | None = None

    model_config = ConfigDict(from_attributes=True)
