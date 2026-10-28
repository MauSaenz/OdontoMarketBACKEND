"""
Esquemas Pydantic v2 para Interacciones del Marketplace (`app/schemas/interaction.py`):
1. Preguntas y Respuestas públicas estilo Mercado Libre (`Question`).
2. Reseñas y Calificaciones con insignia de Compra Verificada (`Review`).
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class InteractionUserSummary(BaseModel):
    """Resumen público y seguro del autor de una pregunta o reseña."""

    id: int
    full_name: str
    clinic_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 1. ESQUEMAS DE PREGUNTAS Y RESPUESTAS (Q&A)
# ==============================================================================


class QuestionCreate(BaseModel):
    """Esquema de entrada cuando un odontólogo publica una pregunta en un producto."""

    question_text: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Pregunta técnica sobre el insumo (caducidad, compatibilidad, lote, etc.)",
        examples=["¿Qué fecha de caducidad tiene el lote actual de esta resina tono A2?"],
    )


class QuestionAnswer(BaseModel):
    """Esquema de entrada cuando el Depósito Dental dueño del producto responde."""

    answer_text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Respuesta oficial del Depósito Dental",
        examples=["¡Hola Doctora! El lote actual LOT-2026-992A caduca en Junio de 2028. Envío inmediato."],
    )


class QuestionResponse(BaseModel):
    """Esquema de salida que se muestra en la página de detalle del producto."""

    id: int
    product_id: int
    user_id: int
    question_text: str
    answer_text: str | None = None
    is_answered: bool
    created_at: datetime
    answered_at: datetime | None = None
    user: InteractionUserSummary | None = None

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 2. ESQUEMAS DE RESEÑAS Y CALIFICACIONES (1 A 5 ESTRELLAS)
# ==============================================================================


class ReviewCreate(BaseModel):
    """Esquema de entrada para calificar un producto dental."""

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Calificación entera de 1 a 5 estrellas",
        examples=[5],
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        examples=["Excelente manipulación y pulido espejo"],
    )
    comment: str = Field(
        ...,
        min_length=5,
        max_length=1500,
        examples=["Llegó con sello original de 3M y caducidad amplia de más de 2 años."],
    )


class ReviewResponse(BaseModel):
    """Esquema de salida con insignia automática de compra verificada (`is_verified_purchase`)."""

    id: int
    product_id: int
    user_id: int
    rating: int
    title: str
    comment: str
    is_verified_purchase: bool
    created_at: datetime
    user: InteractionUserSummary | None = None

    model_config = ConfigDict(from_attributes=True)
