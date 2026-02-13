"""ICD-10 SQLAlchemy models.

This module is intentionally domain-agnostic so it can be reused across multiple systems.
"""

from sqlalchemy import Column, String, Text

from app.core.db import Base


class ICD10(Base):
    __tablename__ = "icd10"

    code = Column(String, primary_key=True, index=True)
    description = Column(String, nullable=False)
    search_terms = Column(Text, nullable=True)
