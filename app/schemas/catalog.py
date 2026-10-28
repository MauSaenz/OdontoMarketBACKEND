"""
Esquemas Pydantic v2 para Categorías Clínicas y Productos Dentales (`app/schemas/catalog.py`).
Valida los atributos técnicos y regulatorios (Registro Sanitario COFEPRIS/FDA, lote,
caducidad, variante de presentación y precios de mayoreo por volumen).
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.user import VendorProfileResponse


# ==============================================================================
# 1. ESQUEMAS DE CATEGORÍAS CLÍNICAS
# ==============================================================================


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=120, examples=["Biomateriales y Operatoria"])
    slug: str = Field(..., min_length=3, max_length=140, examples=["biomateriales-operatoria"])
    description: str | None = None
    icon_name: str = Field(default="Stethoscope", max_length=60)


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 2. ESQUEMAS DE PRODUCTOS DENTALES
# ==============================================================================


class ProductBase(BaseModel):
    """Campos base técnicos, regulatorios y comerciales de un insumo dental."""

    category_id: int = Field(..., gt=0, description="ID de la especialidad odontológica")
    name: str = Field(
        ...,
        min_length=4,
        max_length=220,
        examples=["Resina Filtek Z350 XT Nanorrelleno"],
    )
    sku: str = Field(..., min_length=3, max_length=80, examples=["3M-Z350-A2-4G"])
    description: str = Field(..., min_length=10)

    # Atributos Técnicos y Regulatorios Dentales
    brand: str = Field(..., min_length=2, max_length=120, examples=["3M ESPE"])
    sanitary_registration: str = Field(
        ...,
        min_length=4,
        max_length=120,
        description="Registro Sanitario COFEPRIS o FDA",
        examples=["COFEPRIS 1482C2023 SSA"],
    )
    lot_number: str = Field(..., min_length=2, max_length=80, examples=["LOT-2026-992A"])
    expiration_date: date | None = Field(
        default=None,
        description="Fecha de caducidad (opcional solo en instrumental/equipos que no caducan)",
        examples=["2028-06-30"],
    )
    presentation: str = Field(
        ...,
        min_length=3,
        max_length=180,
        examples=["Jeringa de 4g Tono A2 Body"],
    )
    requires_cold_chain: bool = Field(default=False)

    # Precios y Mayoreo por Volumen
    price: float = Field(..., gt=0, description="Precio unitario de lista (menudeo)")
    wholesale_price: float | None = Field(
        default=None,
        gt=0,
        description="Precio unitario de mayoreo (debe ser menor al precio normal)",
    )
    wholesale_min_qty: int | None = Field(
        default=None,
        ge=2,
        description="Cantidad mínima de unidades para activar el precio de mayoreo",
    )

    # Inventario e Imagen
    stock: int = Field(default=0, ge=0)
    image_url: str = Field(..., min_length=5, max_length=500)
    is_active: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_wholesale_rules(self) -> "ProductBase":
        """
        Regla de negocio odontológica:
        Si el Depósito Dental define un precio de mayoreo (`wholesale_price`),
        1) Debe ser estrictamente menor que el precio unitario normal (`price`).
        2) Debe especificar la cantidad mínima (`wholesale_min_qty`).
        """
        if self.wholesale_price is not None:
            if self.wholesale_price >= self.price:
                raise ValueError(
                    "El precio de mayoreo (wholesale_price) debe ser menor al precio unitario normal (price)."
                )
            if self.wholesale_min_qty is None:
                raise ValueError(
                    "Si defines un precio de mayoreo, debes indicar la cantidad mínima (wholesale_min_qty)."
                )
        return self


class ProductCreate(ProductBase):
    """Esquema de entrada cuando un Depósito Dental publica un nuevo insumo."""
    pass


class ProductUpdate(BaseModel):
    """Esquema de entrada para editar parcialmente un producto o su inventario."""

    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=4, max_length=220)
    description: str | None = Field(default=None, min_length=10)
    brand: str | None = Field(default=None, min_length=2, max_length=120)
    sanitary_registration: str | None = Field(default=None, min_length=4, max_length=120)
    lot_number: str | None = Field(default=None, min_length=2, max_length=80)
    expiration_date: date | None = None
    presentation: str | None = Field(default=None, min_length=3, max_length=180)
    requires_cold_chain: bool | None = None
    price: float | None = Field(default=None, gt=0)
    wholesale_price: float | None = Field(default=None, gt=0)
    wholesale_min_qty: int | None = Field(default=None, ge=2)
    stock: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, min_length=5, max_length=500)
    is_active: bool | None = None


class ProductResponse(ProductBase):
    """Esquema de salida con las relaciones anidadas hacia Categoría y Depósito Dental."""

    id: int
    vendor_id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse | None = None
    vendor: VendorProfileResponse | None = None

    model_config = ConfigDict(from_attributes=True)
