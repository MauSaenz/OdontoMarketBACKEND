"""
Punto de Entrada Principal del Backend (`app/main.py`).
1. Inicializa la aplicación FastAPI con metadatos para OpenAPI / Swagger UI.
2. Configura el evento de ciclo de vida (`lifespan`) para garantizar que las tablas
   y las 6 categorías odontológicas base existan al arrancar el servidor.
3. Configura el Middleware de CORS para permitir peticiones desde Next.js (`localhost:3000`).
4. Conecta todos los routers modulares de OdontoMarket:
   - `auth.router` (/api/auth)
   - `catalog.router` (/api/categories y /api/products)
   - `interactions.router` (/api/products/{id}/questions y /reviews)
   - `orders.router` (/api/orders)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 - Registra todos los modelos en Base.metadata
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models.catalog import Category
from app.routers import auth, catalog, interactions, orders
from init_db import INITIAL_DENTAL_CATEGORIES


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestor de ciclo de vida moderno de FastAPI:
    Se ejecuta automáticamente antes de que el servidor empiece a recibir tráfico HTTP.
    Garantiza que las 8 tablas y las 6 categorías clínicas estén creadas.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Category).count() == 0:
            for cat in INITIAL_DENTAL_CATEGORIES:
                db.add(Category(**cat))
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API RESTful para **OdontoMarket**: E-Commerce Multi-Vendedor especializado en "
        "Productos, Insumos, Biomateriales y Equipos Dentales con trazabilidad COFEPRIS/FDA."
    ),
    lifespan=lifespan,
)

# Configuración de CORS (Cross-Origin Resource Sharing):
# Indispensable para que el navegador permita que el Frontend en Next.js (puerto 3000)
# envíe peticiones con encabezados `Authorization: Bearer <JWT>` hacia FastAPI (puerto 8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de todos los Routers modulares del Marketplace Dental
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(interactions.router)
app.include_router(orders.router)


@app.get(
    "/api/health",
    tags=["Diagnóstico del Sistema"],
    summary="Verificar estado de salud del servidor OdontoMarket",
)
def health_check() -> dict[str, str]:
    """Endpoint ligero para comprobar que FastAPI está en línea."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
