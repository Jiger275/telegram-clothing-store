"""
Сервис для работы с корзиной покупок
"""
from typing import List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models.cart_item import CartItem
from bot.database.models.product import Product
from bot.database.models.product_variant import ProductVariant
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


async def add_to_cart(
    session: AsyncSession,
    user_id: int,
    product_id: int,
    variant_id: Optional[int] = None,
    quantity: int = 1
) -> CartItem:
    """
    Добавить товар в корзину или увеличить количество, если уже есть

    Args:
        session: Сессия БД
        user_id: ID пользователя
        product_id: ID товара
        variant_id: ID варианта товара (опционально)
        quantity: Количество для добавления

    Returns:
        Объект CartItem
    """
    # Проверяем, есть ли уже этот товар в корзине
    query = select(CartItem).where(
        CartItem.user_id == user_id,
        CartItem.product_id == product_id,
        CartItem.variant_id == variant_id
    )
    result = await session.execute(query)
    cart_item = result.scalar_one_or_none()

    if cart_item:
        # Увеличиваем количество
        cart_item.quantity += quantity
        logger.info(
            f"Увеличено количество товара в корзине {cart_item.id} до {cart_item.quantity}"
        )
    else:
        # Создаем новую запись в корзине
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity
        )
        session.add(cart_item)
        logger.info(
            f"Добавлен новый товар в корзину: product_id={product_id}, "
            f"variant_id={variant_id}, quantity={quantity}"
        )

    await session.commit()
    await session.refresh(cart_item)

    return cart_item


async def get_cart_items(
    session: AsyncSession,
    user_id: int
) -> List[CartItem]:
    """
    Получить все товары из корзины пользователя с загрузкой связанных объектов

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Список объектов CartItem с загруженными связями
    """
    query = select(CartItem).where(
        CartItem.user_id == user_id
    ).options(
        selectinload(CartItem.product),
        selectinload(CartItem.variant)
    ).order_by(CartItem.added_at.desc())

    result = await session.execute(query)
    cart_items = result.scalars().all()

    logger.debug(f"Найдено {len(cart_items)} товаров в корзине пользователя {user_id}")

    return list(cart_items)


async def get_cart_item_by_id(
    session: AsyncSession,
    cart_item_id: int,
    user_id: int
) -> Optional[CartItem]:
    """
    Получить конкретный товар из корзины по ID (с проверкой пользователя для безопасности)

    Args:
        session: Сессия БД
        cart_item_id: ID товара в корзине
        user_id: ID пользователя (для проверки безопасности)

    Returns:
        Объект CartItem или None, если не найден
    """
    query = select(CartItem).where(
        CartItem.id == cart_item_id,
        CartItem.user_id == user_id
    ).options(
        selectinload(CartItem.product),
        selectinload(CartItem.variant)
    )

    result = await session.execute(query)
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        logger.warning(
            f"Товар в корзине не найден или доступ запрещен: id={cart_item_id}, user_id={user_id}"
        )

    return cart_item


async def update_cart_item_quantity(
    session: AsyncSession,
    cart_item_id: int,
    user_id: int,
    quantity: int
) -> Optional[CartItem]:
    """
    Обновить количество товара в корзине

    Args:
        session: Сессия БД
        cart_item_id: ID товара в корзине
        user_id: ID пользователя (для проверки безопасности)
        quantity: Новое количество

    Returns:
        Обновленный CartItem или None, если не найден
    """
    cart_item = await get_cart_item_by_id(session, cart_item_id, user_id)

    if not cart_item:
        return None

    if quantity <= 0:
        # Удаляем товар, если количество 0 или отрицательное
        await session.delete(cart_item)
        logger.info(f"Удален товар из корзины {cart_item_id} (количество <= 0)")
    else:
        cart_item.quantity = quantity
        logger.info(f"Обновлено количество товара {cart_item_id} до {quantity}")

    await session.commit()

    return cart_item if quantity > 0 else None


async def remove_cart_item(
    session: AsyncSession,
    cart_item_id: int,
    user_id: int
) -> bool:
    """
    Удалить товар из корзины

    Args:
        session: Сессия БД
        cart_item_id: ID товара в корзине
        user_id: ID пользователя (для проверки безопасности)

    Returns:
        True, если удален, False, если не найден
    """
    cart_item = await get_cart_item_by_id(session, cart_item_id, user_id)

    if not cart_item:
        return False

    await session.delete(cart_item)
    await session.commit()

    logger.info(f"Удален товар из корзины {cart_item_id}")

    return True


async def clear_cart(
    session: AsyncSession,
    user_id: int
) -> int:
    """
    Очистить всю корзину пользователя

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Количество удаленных товаров
    """
    query = delete(CartItem).where(CartItem.user_id == user_id)
    result = await session.execute(query)
    await session.commit()

    count = result.rowcount

    logger.info(f"Очищена корзина пользователя {user_id}: удалено {count} товаров")

    return count


async def get_cart_total(
    session: AsyncSession,
    user_id: int
) -> Decimal:
    """
    Рассчитать общую стоимость всех товаров в корзине

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Общая стоимость как Decimal
    """
    cart_items = await get_cart_items(session, user_id)
    total = Decimal('0.00')

    for item in cart_items:
        if item.product and item.product.is_active:
            item_price = item.product.effective_price * item.quantity
            total += item_price

    logger.debug(f"Общая сумма корзины пользователя {user_id}: {total}")

    return total


async def get_cart_count(
    session: AsyncSession,
    user_id: int
) -> int:
    """
    Получить общее количество товаров в корзине

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Общее количество товаров
    """
    query = select(func.count()).select_from(CartItem).where(
        CartItem.user_id == user_id
    )

    result = await session.execute(query)
    count = result.scalar() or 0

    return int(count)


async def validate_cart_items(
    session: AsyncSession,
    user_id: int
) -> Tuple[List[CartItem], List[str]]:
    """
    Проверить товары в корзине (доступность, активность)

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Кортеж из (валидные товары, список сообщений об ошибках)
    """
    cart_items = await get_cart_items(session, user_id)
    valid_items = []
    errors = []

    for item in cart_items:
        # Проверяем, существует ли товар и активен ли он
        if not item.product or not item.product.is_active:
            errors.append(f"Товар '{item.product.name if item.product else 'Неизвестный'}' больше недоступен")
            continue

        # Проверяем доступность варианта, если указан
        if item.variant_id:
            if not item.variant:
                errors.append(f"Вариант товара '{item.product.name}' не найден")
                continue

            if item.variant.quantity < item.quantity:
                errors.append(
                    f"Недостаточно товара '{item.product.name}' "
                    f"(размер: {item.variant.size}, цвет: {item.variant.color}). "
                    f"Доступно: {item.variant.quantity}, в корзине: {item.quantity}"
                )
                continue

        valid_items.append(item)

    logger.debug(
        f"Проверка корзины пользователя {user_id}: "
        f"{len(valid_items)} валидных товаров, {len(errors)} ошибок"
    )

    return valid_items, errors


def format_cart_item_text(cart_item: CartItem) -> str:
    """
    Форматировать товар из корзины для отображения

    Args:
        cart_item: Объект CartItem

    Returns:
        Отформатированная текстовая строка
    """
    product = cart_item.product
    variant = cart_item.variant

    if not product:
        return "Товар не найден"

    name = product.name
    price = product.effective_price
    quantity = cart_item.quantity
    subtotal = price * quantity

    variant_info = ""
    if variant:
        variant_info = f"\nРазмер: {variant.size}, Цвет: {variant.color}"

    text = (
        f"{name}"
        f"{variant_info}\n"
        f"Цена: {price} ₽ × {quantity} шт.\n"
        f"Итого: {subtotal} ₽"
    )

    return text
