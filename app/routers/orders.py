"""
Router de Órdenes de Compra, Carrito y Checkout Multi-Vendedor (`app/routers/orders.py`).
Implementa el motor financiero y logístico de OdontoMarket:
1. Evaluación automática de precios de mayoreo (`wholesale_price` cuando `quantity >= wholesale_min_qty`).
2. Cálculo de subtotal, IVA (16%) y costo de envío (gratis en compras >= $2,000.00 MXN).
3. Descuento atómico de stock y congelamiento de lote sanitario (`lot_snapshot`) para COFEPRIS/FDA.
4. Historial de pedidos para el Odontólogo comprador y panel de ventas para el Depósito Dental.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user, get_current_vendor_profile, require_vendor
from app.models.catalog import Product
from app.models.enums import OrderStatus, UserRole
from app.models.order import Order, OrderItem
from app.models.user import User, VendorProfile
from app.schemas.order import (
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdate,
)

router = APIRouter(
    prefix="/api/orders",
    tags=["Carrito, Checkout y Órdenes de Compra"],
)

# Constantes financieras de OdontoMarket
TAX_RATE = 0.16                   # 16% de IVA
FREE_SHIPPING_THRESHOLD = 2000.0  # Envío sin costo a partir de $2,000.00
STANDARD_SHIPPING_COST = 180.0    # Costo de envío especializado estándar


def _resolve_unit_price(product: Product, quantity: int) -> tuple[float, bool]:
    """
    Regla financiera de precios por volumen:
    Determina si la cantidad solicitada por el odontólogo alcanza el mínimo requerido
    para activar el precio de mayoreo (`wholesale_price`).
    Devuelve una tupla: `(precio_unitario_aplicado, aplico_mayoreo_bool)`.
    """
    if (
        product.wholesale_price is not None
        and product.wholesale_min_qty is not None
        and quantity >= product.wholesale_min_qty
    ):
        return float(product.wholesale_price), True
    return float(product.price), False


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Procesar Checkout del Carrito y generar Orden de Compra",
)
def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    """
    Ejecuta el Checkout completo dentro de una transacción ACID:
    1. Verifica que cada producto exista, esté activo y tenga stock suficiente.
    2. Aplica automáticamente el precio de mayoreo si `quantity >= wholesale_min_qty`.
    3. Descuenta el stock físico de la tabla `products`.
    4. Congela el lote sanitario (`lot_snapshot`) y el precio (`unit_price`) en `order_items`.
    5. Calcula subtotal, impuestos (16%) y envío, y guarda la orden con estado `Pagado`.
    """
    subtotal_acc = 0.0
    prepared_items: list[OrderItem] = []

    for item_req in order_in.items:
        product = (
            db.query(Product)
            .filter(Product.id == item_req.product_id, Product.is_active.is_(True))
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El producto con ID {item_req.product_id} no existe o ya no está disponible.",
            )

        if product.stock < item_req.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stock insuficiente para '{product.name}'. "
                    f"Solicitaste {item_req.quantity} unidades, pero solo quedan {product.stock} en almacén."
                ),
            )

        # Evaluar si aplica precio de menudeo o de mayoreo por volumen
        unit_price, applied_wholesale = _resolve_unit_price(product, item_req.quantity)
        line_subtotal = round(unit_price * item_req.quantity, 2)
        subtotal_acc += line_subtotal

        # Descontar el inventario del producto
        product.stock -= item_req.quantity

        # Preparar el renglón con el lote y precio congelados
        order_item = OrderItem(
            product_id=product.id,
            vendor_id=product.vendor_id,
            quantity=item_req.quantity,
            unit_price=unit_price,
            applied_wholesale=applied_wholesale,
            lot_snapshot=product.lot_number,
            subtotal=line_subtotal,
        )
        prepared_items.append(order_item)

    subtotal_acc = round(subtotal_acc, 2)
    tax_amount = round(subtotal_acc * TAX_RATE, 2)
    shipping_cost = 0.0 if subtotal_acc >= FREE_SHIPPING_THRESHOLD else STANDARD_SHIPPING_COST
    total_amount = round(subtotal_acc + tax_amount + shipping_cost, 2)

    new_order = Order(
        buyer_id=current_user.id,
        status=OrderStatus.PAGADO,
        subtotal=subtotal_acc,
        tax_amount=tax_amount,
        shipping_cost=shipping_cost,
        total_amount=total_amount,
        shipping_address=order_in.shipping_address.strip(),
        shipping_city=order_in.shipping_city.strip(),
        shipping_state=order_in.shipping_state.strip(),
        shipping_zip=order_in.shipping_zip.strip(),
        notes=order_in.notes.strip() if order_in.notes else None,
        items=prepared_items,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return get_order_by_id(new_order.id, current_user, db)


@router.get(
    "/my-orders",
    response_model=list[OrderResponse],
    summary="Obtener el historial de órdenes compradas por el odontólogo actual",
)
def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Order]:
    """
    Devuelve todas las órdenes realizadas por el usuario autenticado junto con
    sus renglones y la información del producto comprado.
    """
    return (
        db.query(Order)
        .options(
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.vendor),
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.category),
        )
        .filter(Order.buyer_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@router.get(
    "/vendor-sales",
    response_model=list[OrderItemResponse],
    summary="Listar todas las ventas realizadas por el Depósito Dental autenticado",
)
def list_vendor_sales(
    vendor: VendorProfile = Depends(get_current_vendor_profile),
    db: Session = Depends(get_db),
) -> list[OrderItem]:
    """
    Exclusivo para el Panel de Vendedor:
    Gracias a la llave foránea `OrderItem.vendor_id` que diseñamos en la Fase 1,
    el Depósito Dental puede consultar al instante todos los insumos suyos que han sido
    vendidos, incluyendo lote enviado, cantidad e importe.
    """
    return (
        db.query(OrderItem)
        .options(
            joinedload(OrderItem.product).joinedload(Product.category),
            joinedload(OrderItem.product).joinedload(Product.vendor),
            joinedload(OrderItem.order),
        )
        .filter(OrderItem.vendor_id == vendor.id)
        .order_by(OrderItem.id.desc())
        .all()
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Consultar el detalle completo de una orden de compra",
)
def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    """
    Devuelve una orden específica verificando que quien consulta sea el comprador,
    un Depósito Dental que vendió algún artículo de esa orden, o un Administrador.
    """
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.vendor),
            joinedload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.category),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La orden #{order_id} no existe.",
        )

    is_buyer = order.buyer_id == current_user.id
    is_vendor_in_order = (
        current_user.vendor_profile is not None
        and any(item.vendor_id == current_user.vendor_profile.id for item in order.items)
    )
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_buyer or is_vendor_in_order or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para consultar esta orden de compra.",
        )

    return order


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Actualizar estado del pedido (Pendiente -> Pagado -> Enviado -> Entregado)",
)
def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    current_user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> Order:
    """
    Permite al Depósito Dental vendedor o al Administrador actualizar el estado logístico
    de una orden y adjuntar el número de guía de rastreo (`tracking_number`).
    """
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada.",
        )

    if current_user.role != UserRole.ADMIN:
        if not current_user.vendor_profile or not any(
            item.vendor_id == current_user.vendor_profile.id for item in order.items
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta orden no contiene productos de tu Depósito Dental.",
            )

    order.status = status_in.status
    if status_in.tracking_number is not None:
        order.tracking_number = status_in.tracking_number.strip()

    db.commit()
    return get_order_by_id(order.id, current_user, db)
