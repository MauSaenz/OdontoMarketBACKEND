"""
Router del Catálogo Especializado Dental (`app/routers/catalog.py`).
Responsabilidades:
1. Listar y crear Categorías Clínicas (`/api/categories`).
2. Buscador y listado de Productos Dentales (`/api/products`) con filtros combinables:
   texto libre, categoría, marca, rango de precio, solo en stock, solo con mayoreo y ordenamiento.
3. CRUD completo de Productos para los Depósitos Dentales (`/api/products`), validando
   que solo el propietario de la publicación pueda editar o pausar su inventario.
"""

import re
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_vendor_profile, require_vendor
from app.models.catalog import Category, Product
from app.models.enums import UserRole
from app.models.user import User, VendorProfile
from app.schemas.catalog import (
    CategoryCreate,
    CategoryResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(
    prefix="/api",
    tags=["Catálogo Dental y Productos"],
)


def _generate_slug(name: str, sku: str) -> str:
    """
    Genera un identificador URL amigable (slug) único combinando el nombre del insumo y su SKU.
    Ejemplo: 'Resina 3M Filtek Z350' + '3M-Z350-A2' -> 'resina-3m-filtek-z350-3m-z350-a2'
    """
    raw = f"{name}-{sku}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug


# ==============================================================================
# 1. ENDPOINTS DE CATEGORÍAS CLÍNICAS (/api/categories)
# ==============================================================================


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="Listar todas las categorías clínicas dentales",
)
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    """Devuelve las especialidades odontológicas ordenadas alfabéticamente."""
    return db.query(Category).order_by(Category.id.asc()).all()


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva categoría clínica (Requiere rol Vendedor o Admin)",
)
def create_category(
    cat_in: CategoryCreate,
    _current_user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> Category:
    existing = (
        db.query(Category)
        .filter(or_(Category.name == cat_in.name, Category.slug == cat_in.slug))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una categoría con ese nombre o slug.",
        )
    new_cat = Category(**cat_in.model_dump())
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


# ==============================================================================
# 2. ENDPOINTS DE PRODUCTOS DENTALES Y BUSCADOR AVANZADO (/api/products)
# ==============================================================================


@router.get(
    "/products/brands",
    response_model=list[str],
    summary="Obtener lista única de marcas dentales disponibles",
)
def list_available_brands(db: Session = Depends(get_db)) -> list[str]:
    """
    Consulta todas las marcas distintas (`DISTINCT brand`) de productos activos.
    El Frontend en Next.js consume este endpoint para construir dinámicamente los filtros laterales.
    """
    rows = (
        db.query(Product.brand)
        .filter(Product.is_active.is_(True))
        .distinct()
        .order_by(Product.brand.asc())
        .all()
    )
    return [row[0] for row in rows if row[0]]


@router.get(
    "/products/my-inventory",
    response_model=list[ProductResponse],
    summary="Listar el inventario completo del Depósito Dental autenticado",
)
def list_my_vendor_inventory(
    vendor: VendorProfile = Depends(get_current_vendor_profile),
    db: Session = Depends(get_db),
) -> list[Product]:
    """
    Exclusivo para el Panel de Vendedor: devuelve todos los insumos publicados
    por el Depósito Dental actual (incluyendo los agotados o pausados).
    """
    return (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.vendor))
        .filter(Product.vendor_id == vendor.id)
        .order_by(Product.created_at.desc())
        .all()
    )


@router.get(
    "/products",
    response_model=list[ProductResponse],
    summary="Buscar y filtrar productos dentales en el Marketplace",
)
def list_products(
    search: str | None = Query(
        default=None,
        description="Búsqueda por nombre, marca, SKU, registro COFEPRIS o descripción",
    ),
    category_id: int | None = Query(default=None, description="Filtrar por ID de categoría"),
    category_slug: str | None = Query(default=None, description="Filtrar por slug de categoría"),
    brand: str | None = Query(default=None, description="Filtrar por marca fabricante (ej. 3M ESPE)"),
    vendor_id: int | None = Query(default=None, description="Filtrar por Depósito Dental"),
    min_price: float | None = Query(default=None, ge=0, description="Precio mínimo"),
    max_price: float | None = Query(default=None, ge=0, description="Precio máximo"),
    in_stock_only: bool = Query(default=False, description="Solo productos con stock disponible"),
    wholesale_only: bool = Query(
        default=False,
        description="Solo productos que ofrecen descuento de mayoreo por volumen",
    ),
    sort_by: str = Query(
        default="newest",
        description="Criterio de ordenamiento: newest | price_asc | price_desc | name_asc",
    ),
    db: Session = Depends(get_db),
) -> list[Product]:
    """
    Motor de búsqueda del Marketplace Dental:
    Construye dinámicamente una consulta SQL sobre `products` encadenando únicamente
    los filtros que el odontólogo haya seleccionado en la interfaz.
    Utiliza `joinedload` (Eager Loading) para cargar en un solo `JOIN` los datos de la
    Categoría y del Depósito Dental vendedor.
    """
    query = (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.vendor))
        .filter(Product.is_active.is_(True))
    )

    # 1. Filtro de búsqueda de texto libre (insensible a mayúsculas/minúsculas con ILIKE)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(term),
                Product.brand.ilike(term),
                Product.sku.ilike(term),
                Product.sanitary_registration.ilike(term),
                Product.presentation.ilike(term),
                Product.description.ilike(term),
            )
        )

    # 2. Filtro por categoría (por ID numérico o por slug de URL)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if category_slug:
        query = query.join(Product.category).filter(Category.slug == category_slug)

    # 3. Filtro por marca dental
    if brand and brand.strip():
        query = query.filter(Product.brand.ilike(brand.strip()))

    # 4. Filtro por Depósito Dental específico
    if vendor_id is not None:
        query = query.filter(Product.vendor_id == vendor_id)

    # 5. Filtros de rango de precio
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # 6. Filtro de disponibilidad en almacén
    if in_stock_only:
        query = query.filter(Product.stock > 0)

    # 7. Filtro de productos con esquema de mayoreo activo
    if wholesale_only:
        query = query.filter(Product.wholesale_price.is_not(None))

    # 8. Ordenamiento dinámico
    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "name_asc":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    return query.all()


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Obtener la ficha técnica completa de un producto dental por su ID",
)
def get_product_detail(
    product_id: int,
    db: Session = Depends(get_db),
) -> Product:
    """Devuelve toda la información técnica, regulatoria y comercial de un insumo dental."""
    product = (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.vendor))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el producto dental con ID {product_id}.",
        )
    return product


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar un nuevo producto dental (Exclusivo para Depósitos Dentales)",
)
def create_product(
    product_in: ProductCreate,
    vendor: VendorProfile = Depends(get_current_vendor_profile),
    db: Session = Depends(get_db),
) -> Product:
    """
    Crea una nueva publicación en el catálogo asociada automáticamente al `vendor.id`
    del Depósito Dental autenticado.
    """
    # 1. Verificar que la categoría clínica exista
    category = db.query(Category).filter(Category.id == product_in.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La categoría odontológica seleccionada no existe.",
        )

    # 2. Verificar que el código SKU no esté duplicado
    existing_sku = db.query(Product).filter(Product.sku == product_in.sku).first()
    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un producto registrado con el SKU '{product_in.sku}'.",
        )

    slug = _generate_slug(product_in.name, product_in.sku)

    new_product = Product(
        vendor_id=vendor.id,
        slug=slug,
        **product_in.model_dump(),
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # Recargar con relaciones para devolver el esquema completo
    return get_product_detail(new_product.id, db)


@router.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar un producto dental o su stock (Solo el Depósito propietario)",
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    current_user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> Product:
    """
    Actualiza parcialmente los campos enviados en `product_in` (`exclude_unset=True`).
    Verifica que el producto pertenezca al Depósito Dental que hace la petición.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    # Verificar propiedad (a menos que sea Administrador de la plataforma)
    if current_user.role != UserRole.ADMIN:
        if not current_user.vendor_profile or product.vendor_id != current_user.vendor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar un producto que pertenece a otro Depósito Dental.",
            )

    update_data = product_in.model_dump(exclude_unset=True)

    # Validar coherencia de precios si se actualiza precio normal o de mayoreo
    new_price = update_data.get("price", product.price)
    new_wholesale = update_data.get("wholesale_price", product.wholesale_price)
    if new_wholesale is not None and new_wholesale >= new_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El precio de mayoreo debe ser menor al precio unitario normal.",
        )

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return get_product_detail(product.id, db)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="Pausar o desactivar una publicación dental (Soft Delete)",
)
def deactivate_product(
    product_id: int,
    current_user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Realiza un borrado lógico (`is_active = False`) para retirar el producto del buscador
    sin romper la integridad referencial de las órdenes históricas que lo compraron.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    if current_user.role != UserRole.ADMIN:
        if not current_user.vendor_profile or product.vendor_id != current_user.vendor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes desactivar un producto de otro Depósito Dental.",
            )

    product.is_active = False
    db.commit()
    return {"message": f"El producto '{product.name}' ha sido pausado del catálogo activo."}
