"""
Exportación centralizada de todos los esquemas Pydantic v2 de OdontoMarket.
"""

from app.schemas.catalog import (
    CategoryCreate,
    CategoryResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.interaction import (
    QuestionAnswer,
    QuestionCreate,
    QuestionResponse,
    ReviewCreate,
    ReviewResponse,
)
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdate,
)
from app.schemas.user import (
    Token,
    TokenPayload,
    UserCreate,
    UserLogin,
    UserResponse,
    VendorProfileCreate,
    VendorProfileResponse,
    VendorProfileUpdate,
)

__all__ = [
    "VendorProfileCreate",
    "VendorProfileUpdate",
    "VendorProfileResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenPayload",
    "CategoryCreate",
    "CategoryResponse",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "QuestionCreate",
    "QuestionAnswer",
    "QuestionResponse",
    "ReviewCreate",
    "ReviewResponse",
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderCreate",
    "OrderStatusUpdate",
    "OrderResponse",
]
