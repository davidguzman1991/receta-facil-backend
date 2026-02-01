from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from app.core.db import Base


class BaseModel(Base):
    """
    Modelo base con campos comunes para todos los modelos.
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
