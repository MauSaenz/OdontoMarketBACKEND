"""
Capa de Infraestructura de Base de Datos (SQLAlchemy 2.0).
Configura el motor de conexión (Engine), la fábrica de sesiones transaccionales
(SessionLocal), la clase base declarativa (Base) y el generador de inyección
de dependencias (`get_db`) que utilizarán todos los endpoints de FastAPI.
"""

from collections.abc import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# 1. Ajuste específico para SQLite vs PostgreSQL:
# SQLite por defecto restringe que una conexión creada en un hilo (thread) sea usada
# en otro hilo distinto. Como FastAPI maneja peticiones concurrentes en un pool de hilos,
# necesitamos pasar `check_same_thread=False` únicamente cuando usamos SQLite.
# Si cambiamos DATABASE_URL a PostgreSQL en el archivo .env, `connect_args` queda vacío
# y la migración ocurre sin tocar una sola línea de código.
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

# 2. Creación del Motor (Engine) de SQLAlchemy:
# El Engine gestiona el pool de conexiones físicas hacia el motor de base de datos.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # Cambiar a True si deseas ver en consola cada sentencia SQL generada
)


# 3. Activación de integridad referencial (Foreign Keys) en SQLite:
# Por razones históricas, SQLite desactiva el chequeo de llaves foráneas por conexión.
# Este listener intercepta cada conexión nueva en SQLite y ejecuta `PRAGMA foreign_keys=ON`
# para que se comporte exactamente igual que PostgreSQL ante borrados en cascada (CASCADE).
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# 4. Fábrica de Sesiones (SessionLocal):
# Cada instancia de SessionLocal será una sesión de trabajo aislada (Unit of Work)
# para una petición HTTP específica.
# - autocommit=False: nos obliga a hacer `db.commit()` explícito para guardar cambios,
#   permitiendo hacer `db.rollback()` si ocurre una excepción a mitad de una compra.
# - autoflush=False: evita envíos prematuros de SQL antes de que estemos listos.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# 5. Clase Base Declarativa (Estándar SQLAlchemy 2.0):
# Todos nuestros modelos (`User`, `Product`, `Order`, etc.) heredarán de `Base`.
# `Base.metadata` almacena el catálogo de todas las tablas para que SQLAlchemy y Alembic
# puedan crearlas o migrarlas automáticamente.
class Base(DeclarativeBase):
    pass


# 6. Proveedor de Dependencia para FastAPI (`Depends(get_db)`):
# FastAPI ejecuta esta función generadora (`yield`) antes de entrar a un endpoint:
#   a) Abre una sesión limpia de base de datos (`db = SessionLocal()`).
#   b) Se la entrega al endpoint mediante `yield db`.
#   c) Cuando el endpoint responde al cliente (o incluso si lanza un error 500),
#      el bloque `finally` garantiza al 100% que la conexión se cierre (`db.close()`),
#      evitando fugas de memoria o agotamiento de conexiones en producción.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
