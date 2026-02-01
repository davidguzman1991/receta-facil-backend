from sqlalchemy import Column, String

from app.core.db import Base


class ICD10(Base):
    __tablename__ = "icd10"

    code = Column(String, primary_key=True, index=True)
    description = Column(String, nullable=False)
