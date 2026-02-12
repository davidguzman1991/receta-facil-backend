from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.icd10 import ICD10

router = APIRouter(prefix="/icd10", tags=["ICD10"])


@router.get("/search")
def search_icd10(q: str, db: Session = Depends(get_db)):
    """Busca códigos ICD-10 por descripción.

    Nota: si este endpoint devuelve [] en producción, normalmente es porque la tabla
    `icd10` está vacía y debe cargarse ejecutando el seed manual:
    `python -m app.scripts.seed_icd10`.
    """
    stmt = (
        select(ICD10)
        .where(ICD10.description.ilike(f"%{q}%"))
        .limit(20)
    )
    results = db.execute(stmt).scalars().all()
    return [{"code": r.code, "description": r.description} for r in results]
