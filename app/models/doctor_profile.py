import uuid

from sqlalchemy import Column, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name = Column(String(255), nullable=True)
    specialty = Column(String(255), nullable=True)
    senescyt_reg = Column(String(100), nullable=True)
    medical_license = Column(String(100), nullable=True)

    nombres = Column(String(255), nullable=True)
    apellidos = Column(String(255), nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    sexo = Column(String(50), nullable=True)
    pais = Column(String(100), nullable=True)
    provincia = Column(String(100), nullable=True)
    ciudad = Column(String(100), nullable=True)

    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)

    signature_image = Column(String(255), nullable=True)
    stamp_image = Column(String(255), nullable=True)
    signature_url = Column(String(512), nullable=True)
    stamp_url = Column(String(512), nullable=True)

    user = relationship("User")
