import uuid

from sqlalchemy import Column, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Patient(BaseModel):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    dni = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    sex = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    anamnesis = Column(Text, nullable=True)
    personal_history = Column(Text, nullable=True)
    allergic_history = Column(Text, nullable=True)
    gyneco_history = Column(Text, nullable=True)
    surgical_history = Column(Text, nullable=True)

    doctor = relationship("User", foreign_keys=[doctor_id])
    user = relationship(
        "User",
        back_populates="patient_profile",
        foreign_keys=[user_id],
    )
    doctors = relationship(
        "DoctorPatient",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    consultations = relationship(
        "Consultation",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
