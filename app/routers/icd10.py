from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.icd10 import ICD10

router = APIRouter(prefix="/icd10", tags=["ICD10"])


@router.get("/search")
def search_icd10(q: str, db: Session = Depends(get_db)):
    stmt = (
        select(ICD10)
        .where(ICD10.description.ilike(f"%{q}%"))
        .limit(20)
    )
    results = db.execute(stmt).scalars().all()
    return [{"code": r.code, "description": r.description} for r in results]
