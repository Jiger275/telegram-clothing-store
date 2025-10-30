"""
Handler for product viewing and selection
"""
from typing import Optional
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User
from bot.services import product_service
from bot.keyboards.user_keyboards import (
    get_product_card_keyboard,
    get_variant_selection_keyboard
)
from bot.texts.user_messages import (
    PRODUCT_CARD,
    PRODUCT_IN_STOCK,
    PRODUCT_OUT_OF_STOCK,
    SELECT_SIZE,
    SELECT_COLOR,
    PRODUCT_NOT_AVAILABLE
)
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для handlers
router = Router(name="product")

# Временное хранилище для выбранных вариантов (size, color)
# В продакшене лучше использовать FSM или Redis
user_selections = {}


@router.callback_query(F.data.startswith("product:"))
async def show_product(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать карточку товара

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    # Парсим callback data: product:id или product:id:action
    parts = callback.data.split(":")
    product_id = int(parts[1])
    action = parts[2] if len(parts) > 2 else None

    logger.info(f"Пользователь {user.telegram_id} открыл товар {product_id}")

    # Обрабатываем различные действия
    if action == "select_variant":
        await show_variant_selection(callback, user, session, product_id)
        return
    elif action == "size":
        await handle_size_selection(callback, user, session, product_id, parts[3])
        return
    elif action == "color":
        await handle_color_selection(callback, user, session, product_id, parts[3])
        return

    # Получаем товар
    product = await product_service.get_product_by_id(
        session=session,
        product_id=product_id,
        with_variants=True
    )

    if not product or not product.is_active:
        await callback.answer(PRODUCT_NOT_AVAILABLE, show_alert=True)
        return

    # Проверяем доступность
    total_quantity = await product_service.get_product_total_quantity(
        session=session,
        product_id=product_id
    )

    availability = PRODUCT_IN_STOCK if total_quantity > 0 else PRODUCT_OUT_OF_STOCK

    # Формируем описание скидки
    discount_text = ""
    if product.discount_price:
        discount_text = f"Скидка: ~~{product.price} ₽~~ → {product.discount_price} ₽\n"

    # Формируем текст карточки
    text = PRODUCT_CARD.format(
        name=product.name,
        description=product.description or "Нет описания",
        price=product_service.format_price(product.effective_price),
        discount=discount_text,
        availability=availability
    )

    # Проверяем наличие вариантов
    has_variants = len(product.variants) > 0

    keyboard = get_product_card_keyboard(
        product_id=product_id,
        has_variants=has_variants,
        category_id=product.category_id
    )

    # Отправляем с фото, если есть
    if product.images and len(product.images) > 0:
        # Путь к первому изображению
        image_path = f"media/products/{product.images[0]}"

        try:
            photo = FSInputFile(image_path)
            # Удаляем предыдущее сообщение
            await callback.message.delete()
            # Отправляем новое с фото
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения {image_path}: {e}")
            # Если ошибка с изображением, отправляем просто текст
            await callback.message.edit_text(text=text, reply_markup=keyboard)
    else:
        # Без изображения
        await callback.message.edit_text(text=text, reply_markup=keyboard)

    await callback.answer()


async def show_variant_selection(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    product_id: int
) -> None:
    """
    Показать выбор размера и цвета

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
        product_id: ID товара
    """
    # Получаем доступные размеры и цвета
    sizes = await product_service.get_available_sizes(session, product_id)

    # Получаем выбранные параметры пользователя (если есть)
    user_key = f"{user.telegram_id}:{product_id}"
    selected_size = user_selections.get(f"{user_key}:size")
    selected_color = user_selections.get(f"{user_key}:color")

    # Получаем цвета для выбранного размера
    colors = []
    if selected_size:
        colors = await product_service.get_available_colors(
            session,
            product_id,
            size=selected_size
        )

    text = SELECT_SIZE
    if selected_size:
        text += f"\n\nВыбранный размер: {selected_size}\n\n{SELECT_COLOR}"
    if selected_color:
        text += f"\nВыбранный цвет: {selected_color}"

    keyboard = get_variant_selection_keyboard(
        product_id=product_id,
        sizes=sizes,
        colors=colors,
        selected_size=selected_size,
        selected_color=selected_color
    )

    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


async def handle_size_selection(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    product_id: int,
    size: str
) -> None:
    """
    Обработать выбор размера

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
        product_id: ID товара
        size: Выбранный размер
    """
    user_key = f"{user.telegram_id}:{product_id}"

    # Сохраняем выбранный размер
    user_selections[f"{user_key}:size"] = size
    # Сбрасываем цвет при смене размера
    user_selections.pop(f"{user_key}:color", None)

    logger.info(f"Пользователь {user.telegram_id} выбрал размер {size} для товара {product_id}")

    # Обновляем экран выбора
    await show_variant_selection(callback, user, session, product_id)


async def handle_color_selection(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    product_id: int,
    color: str
) -> None:
    """
    Обработать выбор цвета

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
        product_id: ID товара
        color: Выбранный цвет
    """
    user_key = f"{user.telegram_id}:{product_id}"

    # Сохраняем выбранный цвет
    user_selections[f"{user_key}:color"] = color

    logger.info(f"Пользователь {user.telegram_id} выбрал цвет {color} для товара {product_id}")

    # Обновляем экран выбора
    await show_variant_selection(callback, user, session, product_id)


@router.callback_query(F.data.startswith("add_to_cart:"))
async def add_to_cart(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Добавить товар в корзину

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    # Парсим callback data: add_to_cart:product_id или add_to_cart:product_id:size:color
    parts = callback.data.split(":")
    product_id = int(parts[1])
    size = parts[2] if len(parts) > 2 else None
    color = parts[3] if len(parts) > 3 else None

    logger.info(
        f"Пользователь {user.telegram_id} добавляет в корзину товар {product_id}, "
        f"размер={size}, цвет={color}"
    )

    # Проверяем доступность товара/варианта
    is_available = await product_service.check_product_availability(
        session=session,
        product_id=product_id,
        size=size,
        color=color
    )

    if not is_available:
        await callback.answer(PRODUCT_NOT_AVAILABLE, show_alert=True)
        return

    # TODO: Реализовать добавление в корзину в Этапе 5
    # Пока просто уведомляем пользователя
    await callback.answer("Товар добавлен в корзину! (функция будет реализована в следующем этапе)", show_alert=True)

    # Очищаем выбранные параметры
    user_key = f"{user.telegram_id}:{product_id}"
    user_selections.pop(f"{user_key}:size", None)
    user_selections.pop(f"{user_key}:color", None)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery) -> None:
    """
    Обработчик для кнопок без действия (например, индикатор страницы)

    Args:
        callback: Callback query
    """
    await callback.answer()
