import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Consultation(BaseModel):
    __tablename__ = "consultations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    diagnosis = Column(String(255), nullable=True)
    clinical_notes = Column(Text, nullable=True)
    weight = Column(Float, nullable=True)
    blood_pressure = Column(String(20), nullable=True)
    heart_rate = Column(Integer, nullable=True)
    oxygen_saturation = Column(Integer, nullable=True)
    # Campos del acto clínico (Nueva Consulta Médica)
    diagnosis_main = Column(String(255), nullable=True)
    diagnosis_secondary = Column(String(255), nullable=True)
    diagnosis_code = Column(String(20), nullable=True)
    diagnosis_description = Column(String(255), nullable=True)
    general_indications = Column(Text, nullable=True)
    # Registro clínico completo (historia clínica por sesión)
    motivo_consulta = Column(Text, nullable=True)
    enfermedad_actual = Column(Text, nullable=True)
    examen_fisico = Column(Text, nullable=True)
    signos_vitales = Column(JSON, nullable=True)  # ej: {"ta": "120/80", "fc": "72", "peso": "70kg", "talla": "1.70m"}
    plan_tratamiento = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="consultations", foreign_keys=[patient_id])
    doctor = relationship("User", backref="consultations", foreign_keys=[doctor_id])
    vital_signs = relationship(
        "VitalSigns",
        back_populates="consultation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    medications = relationship(
        "ConsultationMedication",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )
