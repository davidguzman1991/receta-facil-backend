from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "ok"}
