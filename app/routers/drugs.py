"""Biblioteca de fármacos: búsqueda y creación."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.drug import Drug
from app.models.user import User
from app.schemas.drug import DrugCreate, DrugOut

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.get("/search", response_model=list[DrugOut])
def search_drugs(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buscar medicamentos por nombre (autocompletado). Requiere autenticación."""
    stmt = (
        select(Drug)
        .where(Drug.name.ilike(f"%{q.strip()}%"))
        .order_by(Drug.name)
        .limit(limit)
    )
    drugs = db.execute(stmt).scalars().all()
    return [DrugOut.model_validate(d) for d in drugs]


@router.post("", response_model=DrugOut, status_code=201)
def create_drug(
    payload: DrugCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear un nuevo fármaco en la biblioteca."""
    drug = Drug(
        name=payload.name.strip(),
        presentation=payload.presentation.strip() if payload.presentation else None,
        strength=payload.strength.strip() if payload.strength else None,
    )
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return DrugOut.model_validate(drug)
