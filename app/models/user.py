"""
Modelos de Usuarios y Perfiles de Vendedor (Depósitos Dentales).
Implementados con la sintaxis declarativa tipada de SQLAlchemy 2.0 (`Mapped` y `mapped_column`).
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import UserRole

# TYPE_CHECKING es True solo para el analizador estático (VS Code / Pyright / MyPy),
# evitando errores de importación circular en tiempo de ejecución entre archivos de modelos.
if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.interaction import Question, Review
    from app.models.order import Order, OrderItem


def utc_now() -> datetime:
    """Genera marcas de tiempo UTC con zona horaria explícita."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    Tabla `users`: Representa a cualquier cuenta registrada en OdontoMarket
    (Odontólogo comprador, Depósito Dental vendedor o Administrador).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Control de roles basado en enumeración estricta
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.CLIENTE,
        nullable=False,
        index=True,
    )

    # Datos profesionales específicos del sector odontológico
    professional_license: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        comment="Cédula profesional del odontólogo (necesaria para compra de anestésicos/uso clínico)",
    )
    clinic_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Nombre del consultorio o clínica dental",
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # ==========================================================================
    # RELACIONES ORM (Navegación bidireccional en Python sin escribir JOINs manuales)
    # ==========================================================================

    # Relación 1-a-1: Si el usuario tiene rol `vendedor`, posee un perfil de Depósito Dental.
    # `uselist=False` indica a SQLAlchemy que un User tiene como máximo un único VendorProfile.
    vendor_profile: Mapped["VendorProfile | None"] = relationship(
        "VendorProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Relación 1-a-N: Un odontólogo puede realizar múltiples órdenes de compra
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="buyer",
        cascade="all, delete-orphan",
    )

    # Relación 1-a-N: Preguntas realizadas por el usuario en las publicaciones
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Relación 1-a-N: Reseñas y calificaciones escritas por el odontólogo
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class VendorProfile(Base):
    """
    Tabla `vendor_profiles`: Almacena los datos fiscales, sanitarios y comerciales
    de los "Depósitos Dentales" o distribuidores que venden en el Marketplace.
    """

    __tablename__ = "vendor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Llave foránea única hacia `users.id` (garantiza relación 1-a-1 a nivel de Base de Datos)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    business_name: Mapped[str] = mapped_column(
        String(180),
        unique=True,
        index=True,
        nullable=False,
        comment="Nombre comercial del Depósito Dental o Casa Comercial",
    )
    tax_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Identificación fiscal del distribuidor (RFC / NIT / RUC)",
    )
    sanitary_license: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="Aviso de Funcionamiento o Licencia Sanitaria (ej. COFEPRIS / FDA)",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si OdontoMarket validó su licencia sanitaria como distribuidor oficial",
    )
    rating_avg: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # ==========================================================================
    # RELACIONES ORM
    # ==========================================================================

    # Conexión inversa hacia la cuenta de usuario dueña de este depósito dental
    user: Mapped["User"] = relationship("User", back_populates="vendor_profile")

    # Relación 1-a-N: Todos los insumos y equipos dentales publicados por este depósito
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="vendor",
        cascade="all, delete-orphan",
    )

    # Relación 1-a-N: Renglones de órdenes vendidos por este depósito dental
    sold_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="vendor",
    )
