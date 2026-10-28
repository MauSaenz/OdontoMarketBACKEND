"""
Modelos del Catálogo Especializado Dental: `Category` y `Product`.
Contempla los atributos regulatorios y clínicos propios de insumos odontológicos:
registro sanitario (COFEPRIS/FDA), lote de fabricación, fecha de caducidad,
variantes de presentación, cadena de frío y esquema de precios por mayoreo/volumen.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.interaction import Question, Review
    from app.models.order import OrderItem
    from app.models.user import VendorProfile


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Category(Base):
    """
    Tabla `categories`: Clasificación clínica del catálogo dental
    (Instrumental Rotatorio, Endodoncia, Ortodoncia, Descartables, Biomateriales, Equipos Mayores).
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_name: Mapped[str] = mapped_column(
        String(60),
        default="Stethoscope",
        nullable=False,
        comment="Nombre del ícono de Lucide Icons que se renderizará en Next.js",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relación 1-a-N: Productos pertenecientes a esta especialidad odontológica
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="category",
    )


class Product(Base):
    """
    Tabla `products`: Publicación de un insumo, biomaterial, instrumental o equipo dental
    ofrecido por un Depósito Dental específico dentro del Marketplace.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Llaves foráneas hacia el Depósito Dental vendedor y la Categoría clínica
    vendor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Identificación comercial
    name: Mapped[str] = mapped_column(String(220), index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(250), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # ==========================================================================
    # ATRIBUTOS TÉCNICOS Y REGULATORIOS DENTALES
    # ==========================================================================
    brand: Mapped[str] = mapped_column(
        String(120),
        index=True,
        nullable=False,
        comment="Fabricante dental (ej. 3M ESPE, Ivoclar Vivadent, NSK, Septodont, Dentsply Sirona)",
    )
    sanitary_registration: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="Número de Registro Sanitario oficial (ej. COFEPRIS 1482C2023 SSA / FDA 510k)",
    )
    lot_number: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        comment="Número de lote actual en almacén para trazabilidad clínica",
    )
    expiration_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Fecha de caducidad (obligatoria en resinas, anestésicos y biomateriales; nula en equipos)",
    )
    presentation: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        comment="Variante de presentación (ej. 'Jeringa 4g Tono A2', 'Caja con 50 cartuchos de 1.8ml')",
    )
    requires_cold_chain: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el biomaterial o insumo requiere control térmico durante el envío",
    )

    # ==========================================================================
    # ESQUEMA DE PRECIOS Y MAYOREO POR VOLUMEN
    # ==========================================================================
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
        comment="Precio unitario de lista (menudeo)",
    )
    wholesale_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Precio unitario preferencial por volumen/mayoreo para clínicas",
    )
    wholesale_min_qty: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Cantidad mínima de unidades para activar automáticamente el precio de mayoreo",
    )

    # ==========================================================================
    # INVENTARIO Y MULTIMEDIA
    # ==========================================================================
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

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
    vendor: Mapped["VendorProfile"] = relationship("VendorProfile", back_populates="products")
    category: Mapped["Category"] = relationship("Category", back_populates="products")

    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product")
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
    )
