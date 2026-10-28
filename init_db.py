"""
Script de Inicialización y Diagnóstico de Base de Datos (Fase 1).
1. Registra todos los modelos en el catálogo `Base.metadata` de SQLAlchemy 2.0.
2. Crea físicamente las 8 tablas relacionales en `odontomarket.db` (o PostgreSQL).
3. Inserta las 6 categorías odontológicas base si la tabla `categories` está vacía.
4. Inspecciona el esquema generado e imprime en consola el resumen de tablas y llaves foráneas.
"""

import sys
from sqlalchemy import inspect
from sqlalchemy.orm import Session

# Aseguramos salida UTF-8 en terminales Windows (PowerShell / CMD)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Importamos el motor y la clase Base desde nuestra capa de infraestructura
from app.core.database import Base, SessionLocal, engine

# Importamos el paquete `app.models` para que Python ejecute las clases y las
# registre dentro de `Base.metadata` antes de llamar a `create_all`.
import app.models  # noqa: F401
from app.models.catalog import Category


INITIAL_DENTAL_CATEGORIES = [
    {
        "name": "Instrumental Rotatorio",
        "slug": "instrumental-rotatorio",
        "description": "Piezas de mano de alta y baja velocidad, micromotores, contrángulos y fresas de carburo/diamante.",
        "icon_name": "Cog",
    },
    {
        "name": "Endodoncia",
        "slug": "endodoncia",
        "description": "Limas rotatorias NiTi, localizadores apicales, conos de gutapercha, cementos selladores e irrigantes.",
        "icon_name": "Activity",
    },
    {
        "name": "Ortodoncia",
        "slug": "ortodoncia",
        "description": "Brackets metálicos y cerámicos, arcos de Niti/Acero, tubos molares, elásticos y adhesivos ortodónticos.",
        "icon_name": "Smile",
    },
    {
        "name": "Descartables y Bioseguridad",
        "slug": "descartables-bioseguridad",
        "description": "Guantes de nitrilo, eyectores de saliva, campos quirúrgicos, bolsas de esterilización y agujas carpule.",
        "icon_name": "ShieldCheck",
    },
    {
        "name": "Biomateriales y Operatoria",
        "slug": "biomateriales-operatoria",
        "description": "Resinas compuestas nanohíbridas, adhesivos universales, ionómeros de vidrio, anestésicos e injertos óseos.",
        "icon_name": "FlaskConical",
    },
    {
        "name": "Equipos Mayores",
        "slug": "equipos-mayores",
        "description": "Unidades dentales completas, autoclaves clase B, lámparas de fotocurado LED, rayos X periapicales y escáneres 3D.",
        "icon_name": "Cpu",
    },
]


def init_database() -> None:
    print("=" * 75)
    print("[ODONTOMARKET] INICIANDO CREACION DE BASE DE DATOS (SQLAlchemy 2.0)")
    print("=" * 75)

    # 1. Crear todas las tablas en la base de datos si no existen
    Base.metadata.create_all(bind=engine)

    # 2. Inspeccionar la base de datos física recién creada
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    print(f"\n[OK] Tablas creadas exitosamente ({len(table_names)} tablas detectadas):")
    for table in sorted(table_names):
        columns = [col["name"] for col in inspector.get_columns(table)]
        fks = inspector.get_foreign_keys(table)
        fk_summary = [f"{fk['constrained_columns'][0]} -> {fk['referred_table']}.id" for fk in fks]
        print(f"   * Tabla [{table}] ({len(columns)} columnas): {', '.join(columns)}")
        if fk_summary:
            print(f"     -> Llaves Foraneas (FK): {', '.join(fk_summary)}")

    # 3. Sembrar las 6 categorías odontológicas iniciales (Idempotente: no duplica si ya existen)
    db: Session = SessionLocal()
    try:
        existing_count = db.query(Category).count()
        if existing_count == 0:
            for cat_data in INITIAL_DENTAL_CATEGORIES:
                db.add(Category(**cat_data))
            db.commit()
            print(f"\n[SEED] Se insertaron las {len(INITIAL_DENTAL_CATEGORIES)} categorias clinicas iniciales.")
        else:
            print(f"\n[INFO] La tabla `categories` ya cuenta con {existing_count} categorias registradas.")
    finally:
        db.close()

    print("\n[EXITO] FASE 1 VERIFICADA: La capa de Base de Datos y ORM esta 100% operativa.")
    print("=" * 75)


if __name__ == "__main__":
    init_database()
