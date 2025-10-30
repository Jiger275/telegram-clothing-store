"""
Handler для работы с корзиной
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User
from bot.services import cart_service
from bot.keyboards.user_keyboards import get_cart_keyboard, get_cart_item_keyboard
from bot.texts.user_messages import (
    CART_EMPTY,
    CART_HEADER,
    CART_TOTAL_FORMAT,
    CART_ITEM_REMOVED,
    CART_CLEARED,
    CART_ITEM_QUANTITY_UPDATED
)
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для handlers
router = Router(name="cart")


@router.message(F.text == "Корзина")
async def show_cart_message(
    message: Message,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать корзину по кнопке из главного меню

    Args:
        message: Объект сообщения
        user: Объект пользователя из БД
        session: Сессия БД
    """
    await show_cart(message, user, session)


@router.callback_query(F.data == "cart")
async def show_cart_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать корзину по callback

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    await show_cart(callback.message, user, session, is_callback=True)
    await callback.answer()


async def show_cart(
    message: Message,
    user: User,
    session: AsyncSession,
    is_callback: bool = False
) -> None:
    """
    Показать содержимое корзины

    Args:
        message: Объект сообщения
        user: Объект пользователя из БД
        session: Сессия БД
        is_callback: Флаг, вызвано ли из callback
    """
    logger.info(f"Пользователь {user.telegram_id} открыл корзину")

    # Получаем товары из корзины
    cart_items = await cart_service.get_cart_items(session, user.id)

    if not cart_items:
        keyboard = get_cart_keyboard(has_items=False)
        if is_callback:
            await message.edit_text(text=CART_EMPTY, reply_markup=keyboard)
        else:
            await message.answer(text=CART_EMPTY, reply_markup=keyboard)
        return

    # Формируем текст корзины
    text = CART_HEADER

    for item in cart_items:
        if not item.product:
            continue

        name = item.product.name
        price = item.product.effective_price
        quantity = item.quantity
        subtotal = price * quantity

        variant_info = ""
        if item.variant:
            variant_info = f"\nРазмер: {item.variant.size}, Цвет: {item.variant.color}"

        text += f"\n{name}{variant_info}\n"
        text += f"Цена: {price} ₽ × {quantity} шт.\n"
        text += f"Итого: {subtotal} ₽\n"
        text += "─────────────────\n"

    # Добавляем общую сумму
    total = await cart_service.get_cart_total(session, user.id)
    text += CART_TOTAL_FORMAT.format(total=total)

    keyboard = get_cart_keyboard(has_items=True)

    if is_callback:
        await message.edit_text(text=text, reply_markup=keyboard)
    else:
        await message.answer(text=text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("cart:increase:"))
async def increase_quantity(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Увеличить количество товара в корзине

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    # Парсим ID товара в корзине
    cart_item_id = int(callback.data.split(":")[-1])

    logger.info(f"Пользователь {user.telegram_id} увеличивает количество товара {cart_item_id}")

    # Получаем товар из корзины
    cart_item = await cart_service.get_cart_item_by_id(session, cart_item_id, user.id)

    if not cart_item:
        await callback.answer("Товар не найден в корзине", show_alert=True)
        return

    # Увеличиваем количество
    new_quantity = cart_item.quantity + 1

    # Проверяем доступность (если есть вариант)
    if cart_item.variant and cart_item.variant.quantity < new_quantity:
        await callback.answer(
            f"Недостаточно товара на складе. Доступно: {cart_item.variant.quantity} шт.",
            show_alert=True
        )
        return

    await cart_service.update_cart_item_quantity(session, cart_item_id, user.id, new_quantity)

    # Обновляем корзину
    await show_cart(callback.message, user, session, is_callback=True)
    await callback.answer(CART_ITEM_QUANTITY_UPDATED)


@router.callback_query(F.data.startswith("cart:decrease:"))
async def decrease_quantity(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Уменьшить количество товара в корзине

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    # Парсим ID товара в корзине
    cart_item_id = int(callback.data.split(":")[-1])

    logger.info(f"Пользователь {user.telegram_id} уменьшает количество товара {cart_item_id}")

    # Получаем товар из корзины
    cart_item = await cart_service.get_cart_item_by_id(session, cart_item_id, user.id)

    if not cart_item:
        await callback.answer("Товар не найден в корзине", show_alert=True)
        return

    # Уменьшаем количество
    new_quantity = cart_item.quantity - 1

    if new_quantity <= 0:
        # Удаляем товар, если количество стало 0
        await cart_service.remove_cart_item(session, cart_item_id, user.id)
        await show_cart(callback.message, user, session, is_callback=True)
        await callback.answer(CART_ITEM_REMOVED)
    else:
        await cart_service.update_cart_item_quantity(session, cart_item_id, user.id, new_quantity)
        await show_cart(callback.message, user, session, is_callback=True)
        await callback.answer(CART_ITEM_QUANTITY_UPDATED)


@router.callback_query(F.data.startswith("cart:remove:"))
async def remove_from_cart(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Удалить товар из корзины

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    # Парсим ID товара в корзине
    cart_item_id = int(callback.data.split(":")[-1])

    logger.info(f"Пользователь {user.telegram_id} удаляет товар {cart_item_id} из корзины")

    # Удаляем товар
    success = await cart_service.remove_cart_item(session, cart_item_id, user.id)

    if success:
        await show_cart(callback.message, user, session, is_callback=True)
        await callback.answer(CART_ITEM_REMOVED)
    else:
        await callback.answer("Товар не найден в корзине", show_alert=True)


@router.callback_query(F.data == "cart:clear")
async def clear_cart(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Очистить корзину

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} очищает корзину")

    # Очищаем корзину
    count = await cart_service.clear_cart(session, user.id)

    # Показываем пустую корзину
    await show_cart(callback.message, user, session, is_callback=True)
    await callback.answer(f"{CART_CLEARED} ({count} шт.)")
