"""
Router de Autenticación, Registro y Gestión de Roles (`app/routers/auth.py`).
Conecta las peticiones HTTP de Login/Registro con:
1. Los esquemas de validación Pydantic v2 (`UserCreate`, `UserLogin`, `Token`).
2. Las funciones criptográficas (`get_password_hash`, `verify_password`, `create_access_token`).
3. Los modelos ORM de SQLAlchemy 2.0 (`User` y `VendorProfile`).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User, VendorProfile
from app.schemas.user import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    VendorProfileCreate,
    VendorProfileResponse,
)

# Prefijo `/api/auth` y etiqueta `Autenticación y Roles` para agrupar en Swagger (/docs)
router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticación y Roles (JWT)"],
)


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo Odontólogo (Cliente) o Depósito Dental (Vendedor)",
)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> Token:
    """
    Registra una nueva cuenta en OdontoMarket y devuelve inmediatamente su token JWT:
    - Verifica que el correo electrónico no esté duplicado.
    - Encripta la contraseña con Bcrypt (`get_password_hash`).
    - Si el usuario envía datos de `vendor_profile`, crea en la misma transacción
      su perfil de Depósito Dental con RFC y Licencia Sanitaria COFEPRIS/FDA.
    """
    # 1. Verificar si el email ya existe en la tabla `users`
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta registrada con este correo electrónico.",
        )

    # 2. Si incluye datos de Depósito Dental, verificar que el nombre comercial sea único
    if user_in.vendor_profile is not None:
        existing_vendor = (
            db.query(VendorProfile)
            .filter(VendorProfile.business_name == user_in.vendor_profile.business_name)
            .first()
        )
        if existing_vendor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un Depósito Dental registrado con ese nombre comercial.",
            )

    # 3. Determinar el rol efectivo (si envía vendor_profile, asignamos rol VENDEDOR)
    effective_role = (
        UserRole.VENDEDOR
        if user_in.vendor_profile is not None
        else user_in.role
    )

    # 4. Instanciar el modelo ORM `User` con contraseña hasheada
    new_user = User(
        email=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=effective_role,
        professional_license=user_in.professional_license,
        clinic_name=user_in.clinic_name,
        phone=user_in.phone,
        is_active=True,
    )
    db.add(new_user)
    # `db.flush()` envía el INSERT a la transacción abierta sin hacer commit todavía,
    # permitiéndonos obtener `new_user.id` para asociarlo al VendorProfile.
    db.flush()

    # 5. Si proporcionó datos de Depósito Dental, crear el registro 1-a-1 en `vendor_profiles`
    if user_in.vendor_profile is not None:
        vendor_data = user_in.vendor_profile.model_dump()
        new_vendor = VendorProfile(
            user_id=new_user.id,
            **vendor_data,
            is_verified=True,  # En entorno demostrativo activamos el sello verificado al registrar licencia
        )
        db.add(new_vendor)

    # 6. Confirmar ambos registros de forma atómica en la base de datos
    db.commit()
    db.refresh(new_user)

    # 7. Emitir el token JWT firmado para que el usuario quede autenticado al instante
    access_token = create_access_token(
        subject=new_user.id,
        role=new_user.role.value,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


def _authenticate_user(email: str, password: str, db: Session) -> User:
    """Función auxiliar interna que verifica email, contraseña Bcrypt y estado activo."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta se encuentra desactivada.",
        )
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión (Estándar OAuth2 Form para Swagger UI)",
)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """
    Endpoint compatible con el botón **Authorize** de la documentación interactiva `/docs`.
    En el estándar OAuth2, el campo `username` del formulario recibe el `email` del usuario.
    """
    user = _authenticate_user(
        email=form_data.username,
        password=form_data.password,
        db=db,
    )
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login-json",
    response_model=Token,
    summary="Iniciar sesión mediante JSON (Ideal para el Frontend en Next.js)",
)
def login_json(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    """
    Endpoint que recibe `{"email": "...", "password": "..."}` en formato JSON puro
    y devuelve el token JWT junto con la información del usuario y su rol.
    """
    user = _authenticate_user(
        email=credentials.email,
        password=credentials.password,
        db=db,
    )
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener perfil del usuario autenticado actual",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Ruta protegida por JWT:
    Decodifica el token enviado en `Authorization: Bearer <token>`, recupera al usuario
    desde la base de datos e incluye su `vendor_profile` si es un Depósito Dental.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/vendor-profile",
    response_model=VendorProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dar de alta o activar perfil de Depósito Dental para el usuario actual",
)
def create_vendor_profile_for_current_user(
    profile_in: VendorProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VendorProfileResponse:
    """
    Permite que un usuario autenticado registre los datos fiscales y sanitarios
    de su Depósito Dental (RFC + Licencia COFEPRIS/FDA) y actualice su rol a `vendedor`.
    """
    if current_user.vendor_profile is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu cuenta ya cuenta con un perfil de Depósito Dental registrado.",
        )

    existing_name = (
        db.query(VendorProfile)
        .filter(VendorProfile.business_name == profile_in.business_name)
        .first()
    )
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un Depósito Dental con ese nombre comercial.",
        )

    new_profile = VendorProfile(
        user_id=current_user.id,
        **profile_in.model_dump(),
        is_verified=True,
    )
    # Si el usuario era `cliente`, promovemos su rol a `vendedor`
    if current_user.role == UserRole.CLIENTE:
        current_user.role = UserRole.VENDEDOR

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return VendorProfileResponse.model_validate(new_profile)
