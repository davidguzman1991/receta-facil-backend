# Backend - Receta Facil

Backend desarrollado con FastAPI, SQLAlchemy 2.0, Alembic y PostgreSQL.

## Requisitos

- Python 3.11.9
- PostgreSQL

## Instalación

1. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
Crear un archivo `.env` en la raíz del backend con:
```
DATABASE_URL=postgresql://user:pass@localhost/receta_facil
SECRET_KEY=your-secret-key-here
```

## Migraciones

1. Crear una nueva migración:
```bash
alembic revision --autogenerate -m "descripción de la migración"
```

2. Aplicar migraciones:
```bash
alembic upgrade head
```

3. Revertir última migración:
```bash
alembic downgrade -1
```

## Ejecutar la aplicación

### Desarrollo local:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Producción (Railway):
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Estructura del proyecto

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py      # Configuración de la aplicación
│   │   ├── db.py          # Configuración de SQLAlchemy
│   │   └── security.py    # Utilidades de seguridad
│   ├── models/
│   │   └── base.py        # Modelo base
│   ├── routers/
│   │   └── health.py      # Endpoint de health check
│   └── main.py            # Aplicación FastAPI
├── alembic/               # Migraciones de base de datos
├── requirements.txt
└── runtime.txt
```

## Endpoints

- `GET /health` - Health check endpoint
