"""FastAPI router for ICD-10.

This router is part of a reusable clinical module intended to be shared across:
- Receta Fácil
- Web Diabetes
- Pediatric version
- Future systems

The module is domain-agnostic and should not depend on other domains like users,
consultations, or prescriptions.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.clinical.icd10.service import _get_icd10_by_code_in_session, _search_icd10_in_session
from app.core.db import get_db

router = APIRouter(prefix="/icd10", tags=["Clinical: ICD10"])


@router.get("/search")
def search(q: str = Query(default=""), limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    results = _search_icd10_in_session(db, query=q, limit=limit)
    return [{"code": r.code, "description": r.description} for r in results]


@router.get("/{code}")
def get_by_code(code: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    item = _get_icd10_by_code_in_session(db, code=code)
    if not item:
        raise HTTPException(status_code=404, detail="ICD10 code not found")
    return {"code": item.code, "description": item.description}
