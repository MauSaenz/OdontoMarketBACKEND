"""
Enumeraciones tipadas del dominio OdontoMarket.
Al heredar de `(str, Enum)`, son compatibles simultáneamente con columnas `Enum` de
SQLAlchemy en la base de datos y con esquemas JSON de Pydantic/FastAPI.
"""

from enum import Enum


class UserRole(str, Enum):
    """Roles de acceso dentro del Marketplace Dental."""

    CLIENTE = "cliente"      # Odontólogo, especialista o clínica dental que compra insumos
    VENDEDOR = "vendedor"    # Depósito dental, fabricante o distribuidor autorizado
    ADMIN = "admin"          # Administrador de la plataforma OdontoMarket


class OrderStatus(str, Enum):
    """Ciclo de vida de una orden de compra dentro del flujo logístico."""

    PENDIENTE = "Pendiente"  # Orden creada, pendiente de confirmación de pago
    PAGADO = "Pagado"        # Pago procesado; el depósito dental prepara el paquete
    ENVIADO = "Enviado"      # En tránsito hacia el consultorio con guía de rastreo
    ENTREGADO = "Entregado"  # Recibido en la clínica dental
    CANCELADO = "Cancelado"  # Orden anulada (con devolución de stock)
