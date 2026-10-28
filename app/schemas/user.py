"""
Esquemas Pydantic v2 para Usuarios, Perfiles de Depósito Dental y Autenticación JWT.
En Clean Architecture, los esquemas Pydantic cumplen dos misiones críticas:
1. Esquemas de Entrada (`Create` / `Update` / `Login`): Validan y sanean el JSON que envía
   el navegador ANTES de tocar la base de datos.
2. Esquemas de Salida (`Response` / `Token`): Filtran qué columnas del modelo SQLAlchemy
   se devuelven al cliente (por ejemplo, NUNCA exponer `hashed_password`).
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


# ==============================================================================
# 1. ESQUEMAS PARA PERFIL DE VENDEDOR (DEPÓSITO DENTAL)
# ==============================================================================


class VendorProfileBase(BaseModel):
    """Campos comunes de un Depósito Dental o distribuidor odontológico."""

    business_name: str = Field(
        ...,
        min_length=3,
        max_length=180,
        description="Nombre comercial del Depósito Dental",
        examples=["Depósito Dental Villa de Cortés S.A."],
    )
    tax_id: str = Field(
        ...,
        min_length=8,
        max_length=50,
        description="RFC / NIT fiscal del distribuidor",
        examples=["DDV2401158A1"],
    )
    sanitary_license: str = Field(
        ...,
        min_length=5,
        max_length=120,
        description="Aviso de Funcionamiento o Licencia Sanitaria (COFEPRIS / FDA)",
        examples=["COFEPRIS-AV-2026-09841"],
    )
    description: str | None = Field(
        default=None,
        description="Descripción comercial y marcas distribuidas",
    )
    logo_url: str | None = Field(default=None, max_length=500)
    city: str = Field(..., min_length=2, max_length=100, examples=["Ciudad de México"])
    state: str = Field(..., min_length=2, max_length=100, examples=["CDMX"])
    address: str = Field(..., min_length=5, max_length=255, examples=["Av. Cuauhtémoc 450, Col. Narvarte"])


class VendorProfileCreate(VendorProfileBase):
    """Esquema de entrada para registrar un nuevo Depósito Dental."""
    pass


class VendorProfileUpdate(BaseModel):
    """Esquema de actualización parcial (todos los campos son opcionales)."""

    business_name: str | None = Field(default=None, min_length=3, max_length=180)
    tax_id: str | None = Field(default=None, min_length=8, max_length=50)
    sanitary_license: str | None = Field(default=None, min_length=5, max_length=120)
    description: str | None = None
    logo_url: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None


class VendorProfileResponse(VendorProfileBase):
    """Esquema de salida serializado desde el modelo ORM `VendorProfile`."""

    id: int
    user_id: int
    is_verified: bool
    rating_avg: float
    created_at: datetime

    # `from_attributes=True` (en Pydantic v2) permite leer directamente objetos de SQLAlchemy
    # como `vendor.business_name` además de diccionarios tradicionales.
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 2. ESQUEMAS PARA USUARIOS (ODONTÓLOGOS, VENDEDORES Y ADMINS)
# ==============================================================================


class UserBase(BaseModel):
    """Atributos públicos básicos de cualquier usuario en OdontoMarket."""

    email: EmailStr = Field(..., examples=["dra.valeria@clinicasmile.com"])
    full_name: str = Field(..., min_length=3, max_length=150, examples=["Dra. Valeria Morales"])
    role: UserRole = Field(default=UserRole.CLIENTE)
    professional_license: str | None = Field(
        default=None,
        max_length=80,
        description="Cédula profesional odontológica",
        examples=["CED-ODON-8492011"],
    )
    clinic_name: str | None = Field(
        default=None,
        max_length=150,
        examples=["Clínica Dental Smile Center"],
    )
    phone: str | None = Field(default=None, max_length=30, examples=["+52 55 1234 5678"])


class UserCreate(UserBase):
    """
    Esquema de entrada para `/api/auth/register`.
    Recibe la contraseña en texto plano (`password`) y opcionalmente los datos
    del Depósito Dental (`vendor_profile`) si el usuario se registra con rol `vendedor`.
    """

    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Contraseña en texto plano (será encriptada con Bcrypt antes de guardarse)",
    )
    vendor_profile: VendorProfileCreate | None = Field(
        default=None,
        description="Datos del Depósito Dental (opcional al registrarse como vendedor)",
    )


class UserLogin(BaseModel):
    """Esquema de entrada JSON para inicio de sesión desde el Frontend en Next.js."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class UserResponse(UserBase):
    """
    Esquema de salida seguro para un Usuario.
    Observa que `password` y `hashed_password` NO existen aquí, garantizando
    que jamás puedan filtrarse en una respuesta HTTP.
    """

    id: int
    is_active: bool
    created_at: datetime
    vendor_profile: VendorProfileResponse | None = None

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 3. ESQUEMAS PARA TOKENS JWT
# ==============================================================================


class Token(BaseModel):
    """Respuesta estándar de autenticación que recibe el Frontend al iniciar sesión."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    """Estructura interna decodificada del JSON Web Token."""

    sub: str | None = None
    role: UserRole | None = None
