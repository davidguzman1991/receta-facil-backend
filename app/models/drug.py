from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.db import Base


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False)
    presentation = Column(String(255), nullable=True)
    strength = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
