"""
Módulo de Seguridad, Criptografía y Autorización JWT (`app/core/security.py`).
Responsabilidades:
1. Encriptar (hashear) contraseñas en texto plano usando el algoritmo Bcrypt.
2. Verificar contraseñas comparando el texto ingresado contra el hash almacenado.
3. Generar y firmar criptográficamente JSON Web Tokens (JWT) con fecha de expiración.
4. Proveer dependencias de FastAPI (`get_current_user`, `require_vendor`, `require_admin`)
   para proteger rutas privadas y validar roles (RBAC: Role-Based Access Control).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User, VendorProfile

# 1. Contexto de Hashing de Contraseñas (Bcrypt):
# Bcrypt incorpora automáticamente un "salt" aleatorio dentro del propio hash resultante,
# protegiendo la base de datos contra ataques de tablas arcoíris (Rainbow Tables).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Esquema OAuth2 para extracción automática del Token Bearer:
# Le indica a FastAPI (y a la interfaz interactiva Swagger en /docs) que las rutas protegidas
# esperan un encabezado HTTP `Authorization: Bearer <token>` y que el token se obtiene en `/api/auth/login`.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara de forma segura una contraseña en texto plano contra el hash Bcrypt
    almacenado en la columna `users.hashed_password`.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Transforma una contraseña en texto plano en un hash irreversible Bcrypt
    de 60 caracteres listo para guardarse en la base de datos.
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Construye y firma un JSON Web Token (JWT) utilizando el algoritmo HS256 y nuestra SECRET_KEY.
    El payload incluye:
      - `sub` (Subject): ID del usuario convertido a string (estándar RFC 7519).
      - `role`: Rol del usuario (`cliente`, `vendedor`, `admin`) para lectura rápida en el Frontend.
      - `exp` (Expiration): Marca de tiempo UTC tras la cual el token deja de ser válido.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


# ==============================================================================
# DEPENDENCIAS DE SEGURIDAD PARA ENDPOINTS DE FASTAPI (Inyección con `Depends`)
# ==============================================================================


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependencia guardiana principal:
    1. Extrae el token del header `Authorization: Bearer <token>`.
    2. Verifica la firma criptográfica y la fecha de expiración con `jwt.decode()`.
    3. Consulta al usuario en la base de datos y comprueba que su cuenta esté activa.
    Si cualquier paso falla, corta la petición devolviendo `HTTP 401 Unauthorized`.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales o el token ha expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta de usuario se encuentra desactivada.",
        )

    return user


def require_vendor(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia de Control de Roles (RBAC):
    Garantiza que únicamente usuarios con rol `vendedor` (Depósito Dental) o `admin`
    puedan ejecutar un endpoint (por ejemplo: publicar un insumo o responder preguntas).
    """
    if current_user.role not in (UserRole.VENDEDOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Se requiere una cuenta de Vendedor (Depósito Dental).",
        )
    return current_user


def get_current_vendor_profile(
    current_user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> VendorProfile:
    """
    Obtiene directamente el objeto `VendorProfile` asociado al usuario vendedor autenticado.
    Si el vendedor aún no ha dado de alta los datos fiscales/sanitarios de su depósito,
    lanza un error `HTTP 400 Bad Request` indicándole cómo completarlo.
    """
    vendor_profile = (
        db.query(VendorProfile)
        .filter(VendorProfile.user_id == current_user.id)
        .first()
    )
    if not vendor_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu cuenta tiene rol de vendedor pero aún no has registrado los datos de tu Depósito Dental.",
        )
    return vendor_profile


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia exclusiva para administradores de la plataforma OdontoMarket.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Se requieren privilegios de Administrador.",
        )
    return current_user
