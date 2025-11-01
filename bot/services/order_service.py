"""
Сервис для работы с заказами
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models.order import Order, OrderStatus, DeliveryType
from bot.database.models.order_item import OrderItem
from bot.database.models.cart_item import CartItem
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


async def generate_order_number(session: AsyncSession) -> str:
    """
    Генерация уникального номера заказа

    Формат: ORD-YYYYMMDD-NNN
    где NNN - порядковый номер заказа за день

    Args:
        session: Сессия БД

    Returns:
        Номер заказа
    """
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"ORD-{today}-"

    # Находим последний заказ за сегодня
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.order_number.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0

    # Генерируем новый номер
    order_number = f"{prefix}{count + 1:03d}"

    return order_number


async def calculate_cart_total(session: AsyncSession, user_id: int) -> Decimal:
    """
    Рассчитать общую стоимость корзины

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Общая сумма
    """
    result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .options(selectinload(CartItem.product))
    )
    cart_items = result.scalars().all()

    total = Decimal('0')
    for item in cart_items:
        if item.product:
            price = item.product.effective_price
            total += price * item.quantity

    return total


async def create_order(
    session: AsyncSession,
    user_id: int,
    customer_name: str,
    customer_phone: str,
    delivery_type: DeliveryType,
    delivery_address: Optional[str] = None,
    comment: Optional[str] = None
) -> Optional[Order]:
    """
    Создать заказ из корзины пользователя

    Args:
        session: Сессия БД
        user_id: ID пользователя
        customer_name: Имя получателя
        customer_phone: Телефон получателя
        delivery_type: Тип доставки (courier или pickup)
        delivery_address: Адрес доставки (для курьера)
        comment: Комментарий к заказу

    Returns:
        Созданный заказ или None если корзина пуста
    """
    # Получаем товары из корзины
    result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .options(
            selectinload(CartItem.product),
            selectinload(CartItem.variant)
        )
    )
    cart_items = result.scalars().all()

    if not cart_items:
        logger.warning(f"Попытка создать заказ с пустой корзиной для пользователя {user_id}")
        return None

    # Рассчитываем общую сумму
    total_amount = Decimal('0')
    order_items_data = []

    for item in cart_items:
        if not item.product:
            continue

        price = item.product.effective_price
        subtotal = price * item.quantity
        total_amount += subtotal

        order_items_data.append({
            'product_id': item.product_id,
            'variant_id': item.variant_id,
            'quantity': item.quantity,
            'price_at_purchase': price,
            'subtotal': subtotal
        })

    # Генерируем номер заказа
    order_number = await generate_order_number(session)

    # Создаем заказ
    order = Order(
        user_id=user_id,
        order_number=order_number,
        total_amount=total_amount,
        status=OrderStatus.NEW,
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_type=delivery_type,
        delivery_address=delivery_address,
        comment=comment
    )

    session.add(order)
    await session.flush()  # Получаем ID заказа

    # Создаем позиции заказа
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            **item_data
        )
        session.add(order_item)

    # Очищаем корзину
    await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id)
    )
    for item in cart_items:
        await session.delete(item)

    await session.commit()

    logger.info(f"Создан заказ {order_number} для пользователя {user_id} на сумму {total_amount}")

    return order


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    """
    Получить заказ по ID

    Args:
        session: Сессия БД
        order_id: ID заказа

    Returns:
        Объект заказа или None
    """
    result = await session.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.items).selectinload(OrderItem.variant)
        )
    )
    return result.scalar_one_or_none()


async def get_order_by_number(session: AsyncSession, order_number: str) -> Optional[Order]:
    """
    Получить заказ по номеру

    Args:
        session: Сессия БД
        order_number: Номер заказа

    Returns:
        Объект заказа или None
    """
    result = await session.execute(
        select(Order)
        .where(Order.order_number == order_number)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.items).selectinload(OrderItem.variant)
        )
    )
    return result.scalar_one_or_none()


async def get_user_orders(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
    offset: int = 0
) -> List[Order]:
    """
    Получить список заказов пользователя

    Args:
        session: Сессия БД
        user_id: ID пользователя
        limit: Количество заказов
        offset: Смещение для пагинации

    Returns:
        Список заказов
    """
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product)
        )
    )
    return list(result.scalars().all())


async def count_user_orders(session: AsyncSession, user_id: int) -> int:
    """
    Подсчитать количество заказов пользователя

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Количество заказов
    """
    result = await session.execute(
        select(func.count(Order.id)).where(Order.user_id == user_id)
    )
    return result.scalar() or 0


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus
) -> Optional[Order]:
    """
    Обновить статус заказа

    Args:
        session: Сессия БД
        order_id: ID заказа
        new_status: Новый статус

    Returns:
        Обновленный заказ или None
    """
    result = await session.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if order:
        order.status = new_status
        await session.commit()
        logger.info(f"Статус заказа {order.order_number} изменен на {new_status}")

    return order


async def cancel_order(session: AsyncSession, order_id: int) -> bool:
    """
    Отменить заказ

    Args:
        session: Сессия БД
        order_id: ID заказа

    Returns:
        True если заказ отменен, False если нет
    """
    result = await update_order_status(session, order_id, OrderStatus.CANCELLED)
    return result is not None


def format_order_details(order: Order) -> str:
    """
    Форматировать детали заказа для отображения

    Args:
        order: Объект заказа

    Returns:
        Отформатированная строка с деталями заказа
    """
    status_emoji = {
        OrderStatus.NEW: "🆕",
        OrderStatus.PROCESSING: "⏳",
        OrderStatus.CONFIRMED: "✅",
        OrderStatus.PREPARING: "📦",
        OrderStatus.READY: "✨",
        OrderStatus.DELIVERING: "🚚",
        OrderStatus.DELIVERED: "🎉",
        OrderStatus.CANCELLED: "❌"
    }

    status_text = {
        OrderStatus.NEW: "Новый",
        OrderStatus.PROCESSING: "В обработке",
        OrderStatus.CONFIRMED: "Подтвержден",
        OrderStatus.PREPARING: "Готовится",
        OrderStatus.READY: "Готов",
        OrderStatus.DELIVERING: "В доставке",
        OrderStatus.DELIVERED: "Доставлен",
        OrderStatus.CANCELLED: "Отменен"
    }

    delivery_text = "🚚 Курьер" if order.delivery_type == DeliveryType.COURIER else "🏪 Самовывоз"

    text = f"Заказ №{order.order_number}\n"
    text += f"Статус: {status_emoji.get(order.status, '')} {status_text.get(order.status, order.status)}\n"
    text += f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"\nПолучатель: {order.customer_name}\n"
    text += f"Телефон: {order.customer_phone}\n"
    text += f"Доставка: {delivery_text}\n"

    if order.delivery_address:
        text += f"Адрес: {order.delivery_address}\n"

    if order.comment:
        text += f"Комментарий: {order.comment}\n"

    text += f"\nСостав заказа:\n"
    text += "─────────────────\n"

    for item in order.items:
        if not item.product:
            continue

        name = item.product.name
        variant_info = ""
        if item.variant:
            variant_info = f" ({item.variant.size}, {item.variant.color})"

        text += f"{name}{variant_info}\n"
        text += f"{item.price_at_purchase} ₽ × {item.quantity} шт. = {item.subtotal} ₽\n"

    text += "─────────────────\n"
    text += f"Итого: {order.total_amount} ₽"

    return text
