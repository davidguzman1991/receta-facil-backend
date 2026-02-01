from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class ConsultationMedication(Base):
    __tablename__ = "consultation_medications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    consultation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drug_id = Column(
        Integer,
        ForeignKey("drugs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dose = Column(String(255), nullable=True)
    route = Column(String(100), nullable=True)
    frequency = Column(String(255), nullable=True)
    duration = Column(String(255), nullable=True)
    quantity = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    drug = relationship("Drug", backref="consultation_medications")
    consultation = relationship("Consultation", back_populates="medications")
