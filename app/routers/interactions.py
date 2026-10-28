"""
Router de Interacciones del Marketplace (`app/routers/interactions.py`).
Implementa dos flujos clave de confianza clínica e interacción comercial:
1. Preguntas y Respuestas públicas estilo Mercado Libre (`/api/products/{id}/questions` y `/api/questions/{id}/answer`).
2. Reseñas y Calificaciones con detección automática de Compra Verificada (`/api/products/{id}/reviews`).
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user, require_vendor
from app.models.catalog import Product
from app.models.enums import UserRole
from app.models.interaction import Question, Review
from app.models.order import Order, OrderItem
from app.models.user import User, VendorProfile
from app.schemas.interaction import (
    QuestionAnswer,
    QuestionCreate,
    QuestionResponse,
    ReviewCreate,
    ReviewResponse,
)

router = APIRouter(
    prefix="/api",
    tags=["Preguntas (Q&A) y Reseñas Verificadas"],
)


# ==============================================================================
# 1. PREGUNTAS Y RESPUESTAS ESTILO MERCADO LIBRE
# ==============================================================================


@router.get(
    "/products/{product_id}/questions",
    response_model=list[QuestionResponse],
    summary="Listar todas las preguntas y respuestas públicas de un producto dental",
)
def list_product_questions(
    product_id: int,
    db: Session = Depends(get_db),
) -> list[Question]:
    """
    Devuelve el hilo de preguntas realizadas por odontólogos junto con las respuestas
    oficiales del Depósito Dental, ordenadas de la más reciente a la más antigua.
    """
    return (
        db.query(Question)
        .options(joinedload(Question.user))
        .filter(Question.product_id == product_id)
        .order_by(Question.created_at.desc())
        .all()
    )


@router.post(
    "/products/{product_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Hacer una pregunta técnica al Depósito Dental vendedor",
)
def ask_product_question(
    product_id: int,
    question_in: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Question:
    """
    Permite a cualquier odontólogo autenticado publicar una pregunta en la página
    del producto (ej. consultar caducidad exacta del lote, compatibilidad de fresas, etc.).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El producto dental consultado no existe.",
        )

    # Evitar que el propio dueño del producto se haga preguntas a sí mismo
    if current_user.vendor_profile and current_user.vendor_profile.id == product.vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes publicar preguntas en un producto de tu propio Depósito Dental.",
        )

    new_question = Question(
        product_id=product_id,
        user_id=current_user.id,
        question_text=question_in.question_text.strip(),
        is_answered=False,
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return (
        db.query(Question)
        .options(joinedload(Question.user))
        .filter(Question.id == new_question.id)
        .first()
    )


@router.put(
    "/questions/{question_id}/answer",
    response_model=QuestionResponse,
    summary="Responder una pregunta de un odontólogo (Exclusivo para el Depósito propietario)",
)
def answer_product_question(
    question_id: int,
    answer_in: QuestionAnswer,
    current_user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> Question:
    """
    Registra la respuesta oficial del Depósito Dental vendedor.
    Verifica estrictamente que la pregunta corresponda a un producto perteneciente
    al Depósito Dental autenticado.
    """
    question = (
        db.query(Question)
        .options(joinedload(Question.product), joinedload(Question.user))
        .filter(Question.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La pregunta indicada no existe.",
        )

    if current_user.role != UserRole.ADMIN:
        if (
            not current_user.vendor_profile
            or question.product.vendor_id != current_user.vendor_profile.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el Depósito Dental dueño de este producto puede responder esta pregunta.",
            )

    question.answer_text = answer_in.answer_text.strip()
    question.is_answered = True
    question.answered_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(question)
    return question


# ==============================================================================
# 2. RESEÑAS Y CALIFICACIONES CON COMPRA VERIFICADA
# ==============================================================================


@router.get(
    "/products/{product_id}/reviews",
    response_model=list[ReviewResponse],
    summary="Listar todas las reseñas y calificaciones de un producto dental",
)
def list_product_reviews(
    product_id: int,
    db: Session = Depends(get_db),
) -> list[Review]:
    """Devuelve las reseñas clínicas de un producto de la más reciente a la más antigua."""
    return (
        db.query(Review)
        .options(joinedload(Review.user))
        .filter(Review.product_id == product_id)
        .order_by(Review.created_at.desc())
        .all()
    )


@router.post(
    "/products/{product_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calificar un producto dental (con detección automática de Compra Verificada)",
)
def create_product_review(
    product_id: int,
    review_in: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Review:
    """
    Registra una calificación de 1 a 5 estrellas y comentario clínico:
    1. Comprueba automáticamente en la tabla `order_items` si este odontólogo compró
       el producto previamente para activar la insignia `is_verified_purchase = True`.
    2. Recalcula en tiempo real la calificación promedio (`rating_avg`) del Depósito Dental.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El producto que intentas calificar no existe.",
        )

    # Verificar si ya dejó una reseña previa en este mismo producto
    existing_review = (
        db.query(Review)
        .filter(Review.product_id == product_id, Review.user_id == current_user.id)
        .first()
    )
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has publicado una reseña para este producto dental.",
        )

    # Comprobar si existe una compra previa real de este usuario para este producto
    prior_purchase = (
        db.query(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.buyer_id == current_user.id,
            OrderItem.product_id == product_id,
        )
        .first()
    )
    is_verified = prior_purchase is not None

    new_review = Review(
        product_id=product_id,
        user_id=current_user.id,
        rating=review_in.rating,
        title=review_in.title.strip(),
        comment=review_in.comment.strip(),
        is_verified_purchase=is_verified,
    )
    db.add(new_review)
    db.flush()

    # Recalcular la reputación promedio (`rating_avg`) del Depósito Dental vendedor
    avg_rating = (
        db.query(func.avg(Review.rating))
        .join(Product, Product.id == Review.product_id)
        .filter(Product.vendor_id == product.vendor_id)
        .scalar()
    )
    if avg_rating is not None:
        vendor = db.query(VendorProfile).filter(VendorProfile.id == product.vendor_id).first()
        if vendor:
            vendor.rating_avg = round(float(avg_rating), 2)

    db.commit()
    db.refresh(new_review)

    return (
        db.query(Review)
        .options(joinedload(Review.user))
        .filter(Review.id == new_review.id)
        .first()
    )
