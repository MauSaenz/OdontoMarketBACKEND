"""
Modelos de Interacción del Marketplace:
1. `Question`: Sistema de Preguntas y Respuestas públicas en la publicación (estilo Mercado Libre),
   donde el odontólogo pregunta dudas técnicas (caducidad, compatibilidad, envío) y el depósito responde.
2. `Review`: Calificaciones (1 a 5 estrellas) y reseñas clínicas con insignia de Compra Verificada.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Question(Base):
    """
    Tabla `questions`: Preguntas públicas en la página de un producto dental
    y la respuesta oficial del Depósito Dental vendedor.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_answered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ==========================================================================
    # RELACIONES ORM
    # ==========================================================================
    product: Mapped["Product"] = relationship("Product", back_populates="questions")
    user: Mapped["User"] = relationship("User", back_populates="questions")


class Review(Base):
    """
    Tabla `reviews`: Reseñas y calificaciones de productos realizadas por odontólogos.
    Incluye el indicador `is_verified_purchase` cuando el comprador adquirió el insumo
    previamente en OdontoMarket.
    """

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Calificación de 1 a 5 estrellas",
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True si el sistema verificó que este odontólogo compró el producto en una orden",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # ==========================================================================
    # RELACIONES ORM
    # ==========================================================================
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")
