"""
Esquemas Pydantic v2 para Órdenes de Compra y Checkout (`app/schemas/order.py`).
Separa claramente qué datos envía el odontólogo al comprar (solo `product_id` y `quantity`,
nunca el precio, por seguridad antifraude) y cómo responde el servidor con los precios
reales, descuentos de mayoreo, impuestos y lote sanitario congelado.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus
from app.schemas.catalog import ProductResponse


class OrderItemCreate(BaseModel):
    """
    Renglón enviado desde el Carrito de Compras en el Frontend.
    NOTA DE SEGURIDAD: El cliente jamás envía `unit_price`; el Backend siempre
    lo consulta de la base de datos y evalúa si aplica precio de mayoreo.
    """

    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=1000, description="Cantidad de unidades a comprar")


class OrderItemResponse(BaseModel):
    """Detalle de un renglón ya procesado y almacenado en la orden."""

    id: int
    order_id: int
    product_id: int
    vendor_id: int
    quantity: int
    unit_price: float
    applied_wholesale: bool
    lot_snapshot: str
    subtotal: float
    product: ProductResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Esquema de entrada del Checkout para generar una nueva Orden de Compra."""

    shipping_address: str = Field(
        ...,
        min_length=5,
        max_length=255,
        examples=["Av. Insurgentes Sur 1602, Consultorio 402"],
    )
    shipping_city: str = Field(..., min_length=2, max_length=100, examples=["Ciudad de México"])
    shipping_state: str = Field(..., min_length=2, max_length=100, examples=["CDMX"])
    shipping_zip: str = Field(..., min_length=4, max_length=20, examples=["03940"])
    notes: str | None = Field(
        default=None,
        max_length=500,
        examples=["Entregar en recepción de la clínica de 9:00 a 18:00 hrs."],
    )
    items: list[OrderItemCreate] = Field(
        ...,
        min_length=1,
        description="Lista de productos del carrito (al menos 1 artículo)",
    )


class OrderStatusUpdate(BaseModel):
    """Esquema para actualizar el estado logístico de la orden y agregar guía de rastreo."""

    status: OrderStatus
    tracking_number: str | None = Field(default=None, max_length=100)


class OrderResponse(BaseModel):
    """Respuesta completa de una Orden de Compra con todos sus renglones e importes."""

    id: int
    buyer_id: int
    status: OrderStatus
    subtotal: float
    tax_amount: float
    shipping_cost: float
    total_amount: float
    shipping_address: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    tracking_number: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
