import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.routers import auth, health
from app.routers.admin import router as admin_router
from app.routers.consultation_medications import router as consultation_medications_router
from app.routers.consultations import router as consultations_router
from app.routers.doctor_consultations import router as doctor_consultations_router
from app.routers.doctor_profile import router as doctor_profile_router
from app.routers.drugs import router as drugs_router
from app.routers.icd10 import router as icd10_router
from app.routers.me import router as me_router
from app.routers.patients import router as patients_router
from app.routers.doctor_patients import router as doctor_patients_router
from app.routers.prescriptions import router as prescriptions_router

logger = logging.getLogger(__name__)
APP_VERSION = "2026-01-31-login-fix"

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://TU_DOMINIO_FRONTEND.com",
]

app = FastAPI(
    title="Receta Facil API",
    description="API backend para Receta Facil",
    version="0.1.0",
)

# CORS: debe ir antes de otras rutas para que las peticiones cross-origin (login desde Next.js) funcionen
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_app_version_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-App-Version"] = APP_VERSION
    return response


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """Para excepciones no controladas: devuelve 500 con cabeceras CORS para que el frontend no vea CORS bloqueado."""
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled exception: %s", exc)
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin in origins:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=cors_headers,
    )


app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(admin_router)
app.include_router(doctor_profile_router)
app.include_router(me_router)
app.include_router(patients_router)
app.include_router(consultations_router)
app.include_router(doctor_consultations_router, prefix="/doctor")
app.include_router(doctor_patients_router, prefix="/doctor")
app.include_router(consultation_medications_router, prefix="/doctor")
app.include_router(drugs_router)
app.include_router(prescriptions_router)
app.include_router(icd10_router)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
if os.path.isdir("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info("App version: %s", APP_VERSION)
    seed_admin_user()
    seed_doctor_demo_user()


def seed_doctor_demo_user() -> None:
    """Crea usuario médico de prueba: doctor@demo.com / 123456 (solo si no existe)."""
    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.email == "doctor@demo.com")).scalar_one_or_none()
        if existing:
            return
        user = User(
            email="doctor@demo.com",
            password_hash=get_password_hash("123456"),
            role="doctor",
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        logger.info("Demo doctor user created (doctor@demo.com)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_admin_user() -> None:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        return

    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.email == settings.ADMIN_EMAIL)).scalar_one_or_none()
        if existing:
            return
        admin = User(
            email=settings.ADMIN_EMAIL,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info("Admin user created")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
