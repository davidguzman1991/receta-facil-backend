"""ICD-10 service layer.

This service is designed to be reused across multiple healthcare products, including:
- Receta Fácil
- Web Diabetes
- Pediatric version
- Future systems

The public API of this module should remain stable even if the search strategy changes
(e.g. adding trigram or full-text search later).
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.clinical.icd10.models import ICD10
from app.core.db import SessionLocal


def _search_icd10_in_session(db: Session, query: str, limit: int = 20) -> List[ICD10]:
    q = query.strip()
    if not q:
        return []

    # Scalability note:
    # - For very large ICD-10 datasets, ILIKE '%query%' on description may become slow.
    # - On PostgreSQL we can use pg_trgm to speed up similarity search with a GIN trigram index.
    # - We keep the function signature stable so the search strategy can evolve (trigram, FTS, etc.)
    #   without changing callers.
    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect, "name", "")
    use_trigram = dialect_name == "postgresql" and len(q) >= 3

    if use_trigram:
        similarity_score = func.similarity(ICD10.description, q)
        stmt = (
            select(ICD10)
            .where(
                or_(
                    ICD10.code.ilike(f"%{q}%"),
                    similarity_score > 0.2,
                )
            )
            .order_by(similarity_score.desc(), ICD10.code.asc())
            .limit(limit)
        )
    else:
        stmt = (
            select(ICD10)
            .where(
                or_(
                    ICD10.code.ilike(f"%{q}%"),
                    ICD10.description.ilike(f"%{q}%"),
                )
            )
            .order_by(ICD10.code.asc())
            .limit(limit)
        )
    return db.execute(stmt).scalars().all()


def _get_icd10_by_code_in_session(db: Session, code: str) -> Optional[ICD10]:
    c = code.strip()
    if not c:
        return None
    stmt = select(ICD10).where(ICD10.code == c)
    return db.execute(stmt).scalar_one_or_none()


def search_icd10(query: str, limit: int = 20) -> List[ICD10]:
    """Search ICD-10 codes.

    This function keeps a stable signature so that search implementation can evolve
    without changing call sites.
    """
    with SessionLocal() as db:
        return _search_icd10_in_session(db, query=query, limit=limit)


def get_icd10_by_code(code: str) -> Optional[ICD10]:
    """Get an ICD-10 entry by its exact code."""
    with SessionLocal() as db:
        return _get_icd10_by_code_in_session(db, code=code)
