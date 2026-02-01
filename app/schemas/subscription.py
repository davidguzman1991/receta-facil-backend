from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubscriptionCreate(BaseModel):
    doctor_id: UUID
    plan: str
    status: str
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    max_recipes_per_cycle: int | None = None
    max_patients: int | None = None


class SubscriptionUpdate(BaseModel):
    plan: str | None = None
    status: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    max_recipes_per_cycle: int | None = None
    max_patients: int | None = None


class SubscriptionOut(BaseModel):
    id: UUID
    doctor_id: UUID
    plan: str
    status: str
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    max_recipes_per_cycle: int | None
    max_patients: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
