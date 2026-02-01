import uuid

from sqlalchemy import Boolean, Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="doctor", server_default=text("'doctor'"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    must_change_password = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    activation_token = Column(String(255), nullable=True, index=True)
    activation_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Reservado para recuperación de contraseña por email (futuro).
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)

    patient_profile = relationship(
        "Patient",
        back_populates="user",
        uselist=False,
        foreign_keys="Patient.user_id",
    )
    patients = relationship(
        "DoctorPatient",
        back_populates="doctor",
        foreign_keys="DoctorPatient.doctor_id",
        cascade="all, delete-orphan",
    )
