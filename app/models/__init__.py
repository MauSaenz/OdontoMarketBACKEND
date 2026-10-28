"""
Registro centralizado de Modelos SQLAlchemy.
Importar todos los modelos aquí es INDISPENSABLE para que `Base.metadata` y `Alembic`
conozcan la existencia de todas las tablas antes de ejecutar `create_all()` o generar migraciones.
"""

from app.models.catalog import Category, Product
from app.models.enums import OrderStatus, UserRole
from app.models.interaction import Question, Review
from app.models.order import Order, OrderItem
from app.models.user import User, VendorProfile

__all__ = [
    "UserRole",
    "OrderStatus",
    "User",
    "VendorProfile",
    "Category",
    "Product",
    "Order",
    "OrderItem",
    "Question",
    "Review",
]
