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

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session

from app.clinical.icd10.models import ICD10
from app.core.db import SessionLocal


def _search_icd10_in_session(db: Session, query: str, limit: int = 20) -> List[ICD10]:
    q = query.strip()
    if not q:
        return []

    # Clinical ranking rationale:
    # - Autocomplete should behave like a clinician expects: when typing the beginning of a diagnosis
    #   (e.g. "diabetes"), the most relevant results are typically those whose *description starts
    #   with* the query.
    # - If there is no strong prefix match, we still want substring matches (useful for diagnoses
    #   where the key term appears in the middle).
    # - Finally, trigram similarity helps recover from typos and small variations.
    #
    # Performance note:
    # - On PostgreSQL we keep pg_trgm-based similarity enabled (GIN index on description) so the
    #   fuzzy layer remains fast at scale.
    # - We combine the tiers in a single query with a CASE-based rank so the database can sort once.
    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect, "name", "")
    use_trigram = dialect_name == "postgresql" and len(q) >= 3

    # Tiered ranking (lower is better):
    # 0: description prefix match
    # 1: description substring match
    # 2: trigram similarity / fuzzy
    prefix_match = ICD10.description.ilike(f"{q}%")
    substring_match = ICD10.description.ilike(f"%{q}%")
    rank_bucket = case(
        (prefix_match, literal(0)),
        (substring_match, literal(1)),
        else_=literal(2),
    )

    # We only compute similarity (and rely on pg_trgm) on PostgreSQL and for non-trivial queries.
    # For other DBs we keep the ordering stable without trigram.
    similarity_score = func.similarity(ICD10.description, q) if use_trigram else literal(0.0)

    # A single query that:
    # - includes prefix/substring matches immediately
    # - includes fuzzy matches via trigram similarity when available
    # - keeps code search compatibility
    stmt = (
        select(ICD10)
        .where(
            or_(
                ICD10.code.ilike(f"%{q}%"),
                prefix_match,
                substring_match,
                similarity_score > 0.2 if use_trigram else literal(False),
            )
        )
        .order_by(rank_bucket.asc(), similarity_score.desc(), ICD10.code.asc())
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
