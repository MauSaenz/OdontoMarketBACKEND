"""
Modelos de Órdenes de Compra (`Order`) y Renglones de Orden (`OrderItem`).
Soportan compras multi-vendedor (un odontólogo puede comprar en un mismo checkout
una resina de un Depósito A y una pieza de mano de un Depósito B) y guardan una
instantánea (snapshot) del precio aplicado (menudeo vs mayoreo) y del lote enviado.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import OrderStatus

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.user import User, VendorProfile


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Order(Base):
    """
    Tabla `orders`: Encabezado de una orden de compra generada en el Checkout.
    Concentra los totales financieros, dirección del consultorio y estado del pedido.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Odontólogo / Clínica que realiza la compra
    buyer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Estado actual del pedido: Pendiente -> Pagado -> Enviado -> Entregado
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.PAGADO,
        nullable=False,
        index=True,
    )

    # Desglose financiero
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    tax_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Impuestos calculados (IVA 16%)",
    )
    shipping_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Costo de envío (gratis a partir de cierto monto o calculado)",
    )
    total_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Suma total cobrada: subtotal + tax_amount + shipping_cost",
    )

    # Datos de entrega en clínica o consultorio dental
    shipping_address: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_state: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_zip: Mapped[str] = mapped_column(String(20), nullable=False)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # ==========================================================================
    # RELACIONES ORM
    # ==========================================================================
    buyer: Mapped["User"] = relationship("User", back_populates="orders")

    # Relación 1-a-N con borrado en cascada: si se elimina la orden, se eliminan sus renglones
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    """
    Tabla `order_items`: Cada línea individual de producto dentro de una orden.
    Guarda `vendor_id` directamente para que cada Depósito Dental pueda consultar
    de inmediato qué productos suyos fueron vendidos sin necesidad de hacer múltiples JOINs.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendor_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Guardamos el precio unitario exacto al momento de la compra (inmutable aunque
    # el vendedor suba el precio del producto la semana siguiente)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    applied_wholesale: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True si la cantidad comprada activó el precio de mayoreo",
    )
    lot_snapshot: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        comment="Lote del producto asignado al momento de la compra para control sanitario",
    )
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    # ==========================================================================
    # RELACIONES ORM
    # ==========================================================================
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
    vendor: Mapped["VendorProfile"] = relationship("VendorProfile", back_populates="sold_items")
