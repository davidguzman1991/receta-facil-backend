from uuid import UUID

from pydantic import BaseModel, EmailStr


class DoctorCreate(BaseModel):
    email: EmailStr
    password: str
    plan: str = "basic"


class DoctorStatusUpdate(BaseModel):
    status: str
