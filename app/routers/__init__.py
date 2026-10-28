"""
Exportación centralizada de los Routers modulares de FastAPI.
"""

from app.routers import auth, catalog, interactions, orders

__all__ = ["auth", "catalog", "interactions", "orders"]
