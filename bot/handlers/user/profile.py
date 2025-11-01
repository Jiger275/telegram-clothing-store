"""
Обработчики для профиля пользователя
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from bot.database.models.user import User
from bot.database.models.order import Order
from bot.keyboards import user_keyboards
from bot.texts import user_messages

router = Router(name="profile")


async def show_profile(message: Message, session: AsyncSession, user: User):
    """
    Показать профиль пользователя

    Args:
        message: Сообщение от пользователя
        session: Сессия БД
        user: Пользователь
    """
    # Получаем количество заказов пользователя
    result = await session.execute(
        select(func.count(Order.id)).where(Order.user_id == user.id)
    )
    orders_count = result.scalar() or 0

    # Форматируем дату регистрации
    created_at = user.created_at.strftime("%d.%m.%Y")

    # Формируем текст профиля
    profile_text = user_messages.PROFILE_INFO.format(
        full_name=user.full_name or "Не указано",
        username=user.username or "не указан",
        created_at=created_at,
        orders_count=orders_count
    )

    # Создаем клавиатуру
    keyboard = user_keyboards.get_profile_keyboard()

    await message.answer(
        profile_text,
        reply_markup=keyboard
    )


@router.message(F.text == "Профиль")
async def profile_handler(message: Message, session: AsyncSession, user: User):
    """
    Обработчик команды "Профиль"

    Args:
        message: Сообщение от пользователя
        session: Сессия БД
        user: Пользователь
    """
    await show_profile(message, session, user)


@router.message(F.text == "Мои заказы")
async def my_orders_handler(message: Message, session: AsyncSession, user: User):
    """
    Обработчик команды "Мои заказы"

    Args:
        message: Сообщение от пользователя
        session: Сессия БД
        user: Пользователь
    """
    # Получаем заказы пользователя
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    if not orders:
        await message.answer(
            user_messages.NO_ORDERS,
            reply_markup=user_keyboards.get_main_menu_keyboard(user.is_admin)
        )
        return

    # Показываем список заказов с пагинацией (первая страница)
    await show_orders_page(message, session, user, orders, page=1)


async def show_orders_page(
    message: Message,
    session: AsyncSession,
    user: User,
    orders: list[Order],
    page: int = 1,
    orders_per_page: int = 5
):
    """
    Показать страницу со списком заказов

    Args:
        message: Сообщение от пользователя
        session: Сессия БД
        user: Пользователь
        orders: Список заказов
        page: Номер страницы
        orders_per_page: Количество заказов на странице
    """
    total_orders = len(orders)
    total_pages = (total_orders + orders_per_page - 1) // orders_per_page

    # Получаем заказы для текущей страницы
    start_idx = (page - 1) * orders_per_page
    end_idx = start_idx + orders_per_page
    page_orders = orders[start_idx:end_idx]

    # Формируем текст с заказами
    text = user_messages.ORDER_HISTORY_HEADER

    for order in page_orders:
        order_date = order.created_at.strftime("%d.%m.%Y %H:%M")
        status_emoji = get_status_emoji(order.status)

        text += f"\n📦 Заказ №{order.order_number}\n"
        text += f"Дата: {order_date}\n"
        text += f"Сумма: {order.total_amount} ₽\n"
        text += f"Статус: {status_emoji} {get_status_text(order.status)}\n"
        text += "─────────────────\n"

    # Создаем клавиатуру с кнопками для каждого заказа и пагинацией
    keyboard = user_keyboards.get_orders_list_keyboard(
        orders=[order for order in page_orders],
        current_page=page,
        total_pages=total_pages
    )

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("orders:page:"))
async def orders_page_handler(callback: CallbackQuery, session: AsyncSession, user: User):
    """
    Обработчик пагинации заказов

    Args:
        callback: Callback запрос
        session: Сессия БД
        user: Пользователь
    """
    page = int(callback.data.split(":")[2])

    # Получаем заказы пользователя
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    # Формируем текст с заказами для текущей страницы
    orders_per_page = 5
    total_pages = (len(orders) + orders_per_page - 1) // orders_per_page

    start_idx = (page - 1) * orders_per_page
    end_idx = start_idx + orders_per_page
    page_orders = orders[start_idx:end_idx]

    text = user_messages.ORDER_HISTORY_HEADER

    for order in page_orders:
        order_date = order.created_at.strftime("%d.%m.%Y %H:%M")
        status_emoji = get_status_emoji(order.status)

        text += f"\n📦 Заказ №{order.order_number}\n"
        text += f"Дата: {order_date}\n"
        text += f"Сумма: {order.total_amount} ₽\n"
        text += f"Статус: {status_emoji} {get_status_text(order.status)}\n"
        text += "─────────────────\n"

    keyboard = user_keyboards.get_orders_list_keyboard(
        orders=[order for order in page_orders],
        current_page=page,
        total_pages=total_pages
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("order:"))
async def order_details_handler(callback: CallbackQuery, session: AsyncSession, user: User):
    """
    Обработчик просмотра деталей заказа

    Args:
        callback: Callback запрос
        session: Сессия БД
        user: Пользователь
    """
    order_id = int(callback.data.split(":")[1])

    # Получаем заказ
    result = await session.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # Формируем детальную информацию о заказе
    order_date = order.created_at.strftime("%d.%m.%Y %H:%M")
    status_emoji = get_status_emoji(order.status)

    text = f"📦 Заказ №{order.order_number}\n\n"
    text += f"Дата создания: {order_date}\n"
    text += f"Статус: {status_emoji} {get_status_text(order.status)}\n\n"

    text += "━━━━━━━━━━━━━━━\n"
    text += "📋 Товары в заказе:\n\n"

    # Загружаем товары в заказе
    await session.refresh(order, ["items"])

    for item in order.items:
        await session.refresh(item, ["product", "variant"])

        variant_info = ""
        if item.variant:
            parts = []
            if item.variant.size:
                parts.append(f"Размер: {item.variant.size}")
            if item.variant.color:
                parts.append(f"Цвет: {item.variant.color}")
            if parts:
                variant_info = f" ({', '.join(parts)})"

        text += f"• {item.product.name}{variant_info}\n"
        text += f"  {item.price_at_purchase} ₽ × {item.quantity} шт. = {item.subtotal} ₽\n\n"

    text += "━━━━━━━━━━━━━━━\n"
    text += f"Общая сумма: {order.total_amount} ₽\n\n"

    text += "📍 Информация о доставке:\n"
    text += f"Получатель: {order.customer_name}\n"
    text += f"Телефон: {order.customer_phone}\n"
    text += f"Способ доставки: {get_delivery_type_text(order.delivery_type)}\n"

    if order.delivery_address:
        text += f"Адрес: {order.delivery_address}\n"

    if order.comment:
        text += f"\n💬 Комментарий: {order.comment}\n"

    # Клавиатура с кнопкой "Назад"
    keyboard = user_keyboards.get_order_details_keyboard()

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "back_to_orders")
async def back_to_orders_handler(callback: CallbackQuery, session: AsyncSession, user: User):
    """
    Обработчик возврата к списку заказов

    Args:
        callback: Callback запрос
        session: Сессия БД
        user: Пользователь
    """
    # Получаем заказы пользователя
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    # Показываем первую страницу
    orders_per_page = 5
    total_pages = (len(orders) + orders_per_page - 1) // orders_per_page

    page_orders = orders[:orders_per_page]

    text = user_messages.ORDER_HISTORY_HEADER

    for order in page_orders:
        order_date = order.created_at.strftime("%d.%m.%Y %H:%M")
        status_emoji = get_status_emoji(order.status)

        text += f"\n📦 Заказ №{order.order_number}\n"
        text += f"Дата: {order_date}\n"
        text += f"Сумма: {order.total_amount} ₽\n"
        text += f"Статус: {status_emoji} {get_status_text(order.status)}\n"
        text += "─────────────────\n"

    keyboard = user_keyboards.get_orders_list_keyboard(
        orders=page_orders,
        current_page=1,
        total_pages=total_pages
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def get_status_emoji(status: str) -> str:
    """
    Получить эмодзи для статуса заказа

    Args:
        status: Статус заказа

    Returns:
        Эмодзи статуса
    """
    status_emojis = {
        "new": "🆕",
        "processing": "⏳",
        "confirmed": "✅",
        "shipped": "🚚",
        "delivered": "📦",
        "cancelled": "❌"
    }
    return status_emojis.get(status, "❓")


def get_status_text(status: str) -> str:
    """
    Получить текстовое описание статуса заказа

    Args:
        status: Статус заказа

    Returns:
        Текст статуса
    """
    status_texts = {
        "new": "Новый",
        "processing": "В обработке",
        "confirmed": "Подтвержден",
        "shipped": "Передан в доставку",
        "delivered": "Доставлен",
        "cancelled": "Отменен"
    }
    return status_texts.get(status, "Неизвестный статус")


def get_delivery_type_text(delivery_type: str) -> str:
    """
    Получить текстовое описание типа доставки

    Args:
        delivery_type: Тип доставки

    Returns:
        Текст типа доставки
    """
    delivery_types = {
        "courier": "Курьер",
        "pickup": "Самовывоз"
    }
    return delivery_types.get(delivery_type, "Не указан")
