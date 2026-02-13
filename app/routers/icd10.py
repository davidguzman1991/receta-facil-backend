from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.clinical.icd10.service import _search_icd10_in_session
from app.core.db import get_db

router = APIRouter(prefix="/icd10", tags=["ICD10"])


@router.get("/search")
def search_icd10(
    q: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Busca códigos ICD-10 por descripción.

    Nota: si este endpoint devuelve [] en producción, normalmente es porque la tabla
    `icd10` está vacía y debe cargarse ejecutando el seed manual:
    `python -m app.scripts.seed_icd10`.
    """
    results = _search_icd10_in_session(db, query=q, limit=limit)
    return [{"code": r.code, "description": r.description} for r in results]
